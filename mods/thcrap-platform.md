# thcrap 平台 —— 改动住在哪、怎么构建、怎么分发

> **版本**：跨版本。本文出现的地址一律带版本前缀（如 `th16:0x442560`）。
> **出处**：thcrap 一手源码 `local/vendor/thcrap` @ `e2e315e`，社区实证
> `local/vendor/thcrap-patches`（ExpHP）。两者都 gitignored，重克隆见 `local/README.md`。
> **可信度**：源码引用全部逐行核准过（§7）；标 ⏳ 的是我们没验过的。

## 0. 结论先行

**thcrap 已经有包管理，包的单位是 patch。代码可以住在 patch 里，不必是 DLL。**

这一条推翻了一个很自然的误判——「简单替换走 patch，复杂逻辑必须写 DLL」。
实证：ExpHP 的 `thcrap-patches` 有 **17 个玩法补丁**（弹幕上限、暂停行为、季节系统、
调试计数器…），覆盖 TH06–TH18，共 **7190 行 asm**，**零个 DLL**。

本文讲三件事：patch 里能装多少能力（§2）、asm 怎么变成 patch（§3）、怎么发出去（§6）。

## 1. 先分清三层

| 层 | 是什么 | 出处 |
| --- | --- | --- |
| 加载 | 挂起启动游戏 → 入口改死循环 → 远程线程 `LoadLibrary thcrap.dll` → 恢复 | `docs/2_files.md` |
| hackpoint | `binhacks` / `codecaves` / `breakpoints`，写在逐版本 `<game>.<build>.js` | `binhack.cpp`、`breakpoint.cpp` |
| 分发 | `repo.js` + `patch.js` + `files.js`，`servers` 可直接指 GitHub raw | `docs/3_repos.md` |

三层互相独立。**「DLL 注入」只属于第一层**，是 thcrap 加载自己的方式，
不等于「你的 mod 必须是 DLL」。

## 2. ★ patch 里能装多少能力

| 机制 | 一手出处 | 意味着 |
| --- | --- | --- |
| 每个 codecave 的名字进全局函数表 | `binhack.cpp:1689` | patch 里的代码块可**按名字被调用**，与 DLL 导出平级 |
| 名字前缀是 `codecave:` | `binhack.cpp:1599` | 表达式里写 `codecave:NAME`；后缀匹配不受前缀影响 |
| `"export": true` + 名字含 `_patch_init` | `binhack.cpp:1724` → `plugin.cpp:304` | **patch 加载时被 thcrap 直接调用**，无需 DLL 就有初始化钩子 |
| 内置 `BP_patch_func_run_all` | `plugin.cpp` 末尾 | JSON 里的断点按 pattern 分发到 patch 代码，`param` 可从寄存器表达式算 |
| `size` 有、`code` 无的 codecave | `binhack.cpp:1451` | 一块**具名、可寻址的 RW 内存** → 跨帧状态，不必在 DLL 里开全局变量 |
| ~200 个 `th_*` 函数按名字暴露 | `plugin.cpp` 开头的 `funcs` 表 | codecave 里写 `[th_malloc]` 就能调 malloc/sprintf/qsort/sin/GetProcAddress… |

最后一条是决定性的：**那张表存在的唯一理由，就是让 patch 里的机器码能用 C 运行时**。
如果 thcrap 认为复杂逻辑该住在 DLL 里，不需要给 codecave 暴露 `sprintf` 和 `qsort`。

### 生态本身就是「一个 DLL + N 个 patch」

`thcrap_tsa`（官方游戏支持插件）导出 **34 个 `BP_*`**——`BP_spell_name`、`BP_music_title`、
`BP_gentext`、`BP_th06_file_load`…… 然后**几百个翻译 patch 按名字消费这些能力**，自己不带代码。

patch 之间还能再叠一层：ExpHP 的 `base_exphp` 自述 *"Provides functions that help other
patches…"*，`c_key` 自述 *"for use by other patches"*。**能力层不一定要是 DLL。**

## 3. ★ asm 路线：怎么把汇编变成 patch

### 3.1 目录形状（照抄 ExpHP `bullet_cap`）

```
patches/<patch_id>/
├── patch.js              id / title / servers / dependencies
├── files.js              文件名 → crc32(由 repo_update.py 生成)
├── binhacks.py           ★ 构建脚本:调 binhack_helper,吐出 .js
├── common.asm            跨版本的宏 / 结构体定义
├── options.yaml          可配置项(§4)
├── th16.v1.00a.asm       ← 人写这个
├── th16.v1.00a.js        ← 脚本生成,入库
├── th18.v1.00a.asm
└── th18.v1.00a.js
```

`.asm` 是源，`.js` 是产物，**两者都入库**——因为 thcrap 只认 `.js`，而 `.asm` 是给人读的。

### 3.2 asm → hex：keystone + 符号定位

核心在 `scripts/binhack_helper.py`。流程：

1. `keystone.Ks(KS_ARCH_X86, KS_MODE_32)` 汇编 asm 字符串。
2. **符号定位技巧**：凡是要变成 thcrap 表达式的位置，先塞一个一次性符号；
   把同一段 asm **汇编多次、每次翻转该符号的位**，看输出哪 4 个字节跟着变
   → 就定位到了它在字节流里的 `[start, stop)`。
3. 把那 4 个字节替换成 thcrap 的 `[expr]` / `<expr>` 文本，其余照原样转 hex。

产物形如 `55 8b ec … e8 [codecave:foo] … c3`——**hex 串里嵌 thcrap 表达式**，
所以 cave 不必自己做重定位，绝对地址交给 thcrap 在 apply 时渲染。

> 这套 `binhack_helper.py` 是现成可抄的（ExpHP 仓库无 LICENSE，与 `th-re-data` 同样情况：
> 可研究可借鉴，正式发布注明出处）。

### 3.3 keystone 的三个坑（直接照抄它的 footgun 检查）

`_check_asm_for_footguns()` 拦三种写法，每一种都会**静默出错**：

| 坑 | 症状 | 写法 |
| --- | --- | --- |
| size 操作数漏 `ptr` | keystone「成功」返回 `None` | 一律写 `dword ptr [...]` |
| 整数带前导 0 | 被当八进制 | 别写 `0755` |
| 十进制整数 | keystone #481 会把默认基数改成 16 | **一律 `{:#x}` 格式化** |

第三条尤其阴——`mov eax, 30` 可能被汇编成 `0x30`。**所有立即数写十六进制。**

### 3.4 表达式：相对 vs 绝对（我们踩过的坑，别再踩）

`[expr]` = **相对**（渲染为相对 patch 处的 dword 偏移，所以 `E9 [codecave:X]` 能当 jmp）；
`<expr>` = **绝对**。→ **写函数指针表槽必须用 `<…>`**，写成 `[…]` 会把相对偏移当指针用。
出处 `binhack.cpp`；实例见
[`th16.v1.00a/tracking-laser/patch/thcrap_patch.md`](th16.v1.00a/tracking-laser/patch/thcrap_patch.md) §0。

### 3.5 ⏳ 我们还没验的：C → flat binary

ExpHP 全程手写 asm。若想用 C 写 cave，需要：编译成 position-independent 的
flat binary、无 CRT 无导入表、外部调用换成 `[th_xxx]` 或绝对地址、再转 hex。
**这条链路本仓未验证**，不要当成已知可行。想用 C 又不想验这条，走 §5 的路线 B。

## 4. options：把会变的量推出代码

ExpHP 的 `options.yaml` → 生成 js。形状：

```yaml
options:
  bullet-cap.bullet-cap:
    type: "i32"
    val:
      /value-if(th09): -1
      /value-if(any(th10..th18)): 0x7d00
```

代码里用 `<option:bullet-cap.bullet-cap>` 引用，DLL 里用 `patch_opt_get()` 读。

**设计原则：地址、`expected`、数值、开关全部推到 JSON，代码里只留逻辑。**
这样换 exe build 或调参数时，用户更新 patch 就够，不必重发二进制。
这条与 [`_template/TARGET.md`](_template/TARGET.md) 的死绑登记是同一件事的两面——
登记表里的每一项，理想情况下都该是 JSON 里的一行，而不是源码里的一个常量。

## 5. 两条路线与选择判据

| 路线 | `bin/` 里的 DLL 数 | 走包管理 | 代价 |
| --- | --- | --- | --- |
| **A. 纯 patch**（codecave + asm） | 0 | ✅ 完全 | 手写 asm；调试最难；C 路线未验（§3.5） |
| **B. 一个 dispatcher DLL + N 个 patch** | **O(1)** | ✅ mod 全走 | DLL 要手动装一次；接口要先设计 |
| C. 每个 mod 一个 DLL | **O(N)** | ❌ | 无包管理，`bin/` 越堆越乱。**不要** |

**判据**：

- 改动**规整、写完基本不动**（改常量、扩容、改判定）→ **A**。ExpHP 全部属于此类。
- 要**加一个子系统**、且需要**反复迭代**（自定义对象/vtable、新注册表、存档兼容）→ **B**。
  `card-rework` 属于此类：C 的可调试性值得付「手动装一次 DLL」的代价。
- **C 永远不选。**

### B 的不变量

**DLL 数量不随 mod 数量增长。** 注意不是「恰好一个」——thcrap 自己 `bin/` 里就有好几个 DLL
（`thcrap.dll` / `thcrap_tsa` / `thcrap_tasofro` / `thcrap_update` / `thcrap_bgmmod`…），
它们全是能力层，几百个 patch 共用。**致命的从来不是数量，是「每个 mod 一个 DLL」**——
那时 DLL 数随 mod 数线性增长，B 就退化成 C。

判据一问就有答案：**新加一个 mod，`bin/` 里的文件变多了吗？**

推论：DLL 只提供**能力**（`BP_*`、工具函数），不承载某个具体 mod 的**身份与数据**；
地址、`expected`、数值、开关一律住在 patch（§4）。

**例外：一次性探针。** 像 [`th18.v1.00a/runtime-probe`](th18.v1.00a/runtime-probe/README.md)
这种刻意不依赖 thcrap 任何 API、只为把变量降到最少的独立 DLL，不受此约束——
它不是 mod、不进分发，验完即弃或折进 dispatcher。

**B 可以逐个迁往 A**：某个 mod 的逻辑稳定下来后，用 §3 的链路把它汇编进 codecave、
从 DLL 里摘掉。B 是中间态，不是死路。

### B 的两端怎么连

DLL 的导出与 patch 的 codecave **进的是同一张函数表**
（`plugin.cpp:324` vs `binhack.cpp:1689`），表达式按名字取（`expression.cpp:1440`）：

- patch 写 `"breakpoints": {"card_alloc": {…}}` → thcrap 去找导出的 `BP_card_alloc`（`breakpoint.cpp:335`）。
- patch 写 `"code": "e8 [MyDispatch]"` → 调 DLL 导出的 `MyDispatch`。

**缺 DLL 时优雅降级**：记一行 `ERROR: function '…' not found!` 并**跳过该 hackpoint**
（`binhack.cpp:39`），不崩、不影响别的 patch。默认只写日志，run config 里开
`msgbox_invalid_func` 才弹框。

## 6. 分发

### 6.1 patch：push 到 GitHub 就是发布

ExpHP 的 `repo.js` / `patch.js` 里 `servers` 直接指 raw：

```json
"servers": ["https://raw.githubusercontent.com/ExpHP/thcrap-patches/master/patches/"]
```

**不用架服务器、不用 CDN**。thcrap 按 `files.js` 的 crc32 拉增量。

| 文件 | 关键字段（源码实读） |
| --- | --- |
| `repo.js` | `id` / `title` / `contact` / `patches`（决定 configure 里能勾到什么）/ `servers` / `neighbors` |
| `patch.js` | `id`（缺省回退成目录名）/ `version` / `title` / `servers` / `dependencies` / `supported_games` / `ignore` / `update` / `motd` |
| `files.js` | `{"相对路径": crc32 整数}`，值为 `null` = **删除该文件**。用 `scripts/repo_update.py` 生成，别手写 |

用户装法两种：让 thpatch 的 `repo.js` 把你列进 `neighbors`，或者直接把 repo 根 URL
作命令行参数喂给 `thcrap_configure`（完全绕开 thcrap 网络）。

### 6.2 本地测试不需要服务器

run config（`config/*.js`）里每个 patch 项的 `archive` = patch 根目录，
相对 thcrap 根或绝对路径均可。配上 `patch.js` 里 `"update": false`，
thcrap 就不会去同步一个不存在的远端。然后 `thcrap_loader.exe myconfig.js th18`。

### 6.3 DLL 不走这条路

插件**只从 `<thcrap>/bin` 加载**（`init.cpp:333`）。「从 patch 目录加载 DLL」的代码
写好了但被注释掉，原文 *"Potentially dangerous stuff. Do not want!"*（`init.cpp:337-346`）。
**这是安全决定，不会改。** 所以带 DLL 的 mod 永远是两件套：DLL 手动放 bin，patch 走 repo。

DLL 侧的两条硬关卡（错了会被**静默**忽略）：

- **导出名必须无装饰**：thcrap 在 `LoadLibrary` 之前先扫 PE 导出表找 `thcrap_plugin_init`
  （`pe.cpp:88`）。x86 `__stdcall` 不经 `.def` 会被装饰成 `_thcrap_plugin_init@0`。
- **位数必须匹配**：`plugin.cpp:355`。

### 6.4 不分发游戏字节

thcrap 本身是公有领域（`UNLICENSE.txt`），法律上可转发，但**别打包**——
它自带更新器、用户多半已装、`thcrap_configure` 的引导你复刻不了。
游戏 exe/dat 一律不发。发布物 = 你的 patch/DLL + 源码 + 文档 + 预期原字节。

## 7. 一手出处对照

引用的都是 `local/vendor/thcrap` @ `e2e315e`，行号逐条核准过。

| 结论 | 出处 |
| --- | --- |
| 插件只从 `<thcrap>/bin` 加载 | `init.cpp:333` |
| patch 目录加载 DLL 被注释掉 | `init.cpp:337-346` |
| 卸载顺序：先 `exit` 钩子再 `FreeLibrary` | `init.cpp:459-460` |
| 加载前先扫导出表找 `thcrap_plugin_init` | `pe.cpp:88` |
| 位数不符则拒绝 | `plugin.cpp:355` |
| 插件所有导出进全局函数表 | `plugin.cpp:324` |
| `export: true` 的 codecave 被当 patch 函数调用 | `binhack.cpp:1724` → `plugin.cpp:304` |
| 所有 codecave 名字进全局函数表 | `binhack.cpp:1689` |
| codecave 名字前缀 `codecave:` | `binhack.cpp:1599` |
| 断点函数名 = `BP_` + JSON key | `breakpoint.cpp:335` |
| 表达式里裸名字先查函数表 | `expression.cpp:1440` |
| 函数找不到 → 记日志并跳过 | `binhack.cpp:39` |
| keystone 用法与三个坑 | ExpHP `scripts/binhack_helper.py` |
