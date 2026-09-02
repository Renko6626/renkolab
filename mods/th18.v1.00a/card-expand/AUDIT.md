# AUDIT —— card-expand 对抗审计

> **版本**：TH18 v1.00a（`th18.exe`，imagebase `0x400000`）。本文裸地址默认属该版本；引用其他版本须写成 `th16:0x…`。
> 姿态：**默认自己写错了，去二进制找证伪证据**。逐条给 CONFIRMED / REFUTED / OPEN。
> 清单来自 [`../../_template/AUDIT-checklist.md`](../../_template/AUDIT-checklist.md)。

## 0. 状态

**静态审计通过；游戏内未实跑。**产出是第 1 步（行数仍 58，行为应零变化）的 patch。

## A. ABI / 栈平衡

| # | claim | 结论 |
| --- | --- | --- |
| A1 | 初始化 codecave 不调用任何引擎函数 | **CONFIRMED** —— 全文只有 `cld/pushad/mov/rep movsd/popad/ret`，见 A5 反汇编 |
| A2 | 调用约定是 cdecl、调用方清栈，所以结尾用裸 `ret` | **CONFIRMED** —— `plugin.h:71` `typedef void (TH_CDECL *mod_call_type)(void *param)`；`plugin.cpp` 的 `mod_funcs_t::run` 直接 `func(param)` |
| A3 | cdecl 要求被调方保留的 `ebx/esi/edi/ebp` 都被保住 | **CONFIRMED** —— `pushad`/`popad` 覆盖全部 8 个通用寄存器 |
| A4 | `rep movsd` 依赖 DF=0 | **CONFIRMED** —— 入口显式 `cld`；且 `popad` 不恢复标志，返回时 DF 仍为 0，符合 ABI 要求 |
| A5 | 生成的机器码就是设计的那些指令 | **CONFIRMED** —— 见下 |
| A6 | FPU 栈平衡 | **CONFIRMED** —— 全程不碰 x87/SSE |

反汇编（`<…>` 表达式用 `deadbeef` 占位，每个恰好 4 字节）：

```
rows=58                          rows=255 追加的填充循环
 0: cld                          13: mov  ebx, 0xc5        ; 255-58 = 197
 1: pusha                        18: mov  esi, <新表+0xb60> ; 行 56 (NULL)
 2: mov  edi, <新表>             1d: mov  ecx, 0xd          ; 0x34/4 = 13
 7: mov  esi, <Rxc53c0>          22: rep  movsd
 c: mov  ecx, 0x2f2   ; 754      24: dec  ebx
11: rep  movsd                   25: jne  0x18              ; 回到 mov esi
13: popa
14: ret
```

`jne 0x18` 的目标正好落在循环体首指令上 —— **CONFIRMED**（rel8 = −15，体长 13 + 跳转 2）。

## B. 写入点

| # | claim | 结论 |
| --- | --- | --- |
| B1 | 100 处 `expected` 与 exe 实际字节逐字节一致 | **CONFIRMED** —— `make verify` 从**已生成的 patch 文件**回到 exe 重新比对，不是复用生成器的中间结果 |
| B2 | 只替换 4 字节常量，opcode 一字不动 | **CONFIRMED** —— `verify_patch` 第 ③ 项逐条比对 `code` 前缀与 `expected` 前缀 |
| B3 | `code` 与 `expected` **渲染后等长** | **CONFIRMED** —— 二者由同一条记录产出。⚠️ 这条不是形式主义：长度不等时 thcrap 会「记一行日志然后**跳过校验**」（`binhack.cpp:1264`），护栏白装 |
| B4 | 绝对 `<…>` 用对了，不该是相对 `[…]` | **CONFIRMED** —— 100 处全是 `mov r32, imm32` / `cmp r32, imm32` / `add`/`lea`，常量是**当值用的地址**，不是 rel32。（`tracking-laser` 的历史教训正相反：数据指针表槽误写成 `[…]`）|
| B5 | 目标落在 `.text`，thcrap apply 时会设页可写 | **CONFIRMED** —— `.text` VA `0x401000` 长 `0xab800`，100 处全在内 |
| B6 | 零售表本身不被写 | **CONFIRMED** —— 只在初始化时**读**它一次（`rep movsd` 的源） |

## C. 完整性 —— 「100 处就是全集」怎么证的

这是本 mod 最要紧的一条：**漏一处的后果远大于改错一处**。三层证据：

| # | 检查 | 结果 |
| --- | --- | --- |
| C1 | 骨架锚点（`add r32,0x34` 紧跟 `inc r32`）在全 `.text` 的出现次数 | **正好 25 处**，与 25 个内联查表一一对应 |
| C2 | 扫「表基 / 回退行 / 表尾」三段值，列出不在骨架里的 | 15 处，**全部**是 `0x4c5f88` / `0x4c5f8c` 那两个热全局 |
| C3 | 扫**整张表区间** `0x4c53c0`–`0x4c5f88` 的全部 4 字节引用 | `.text` **0 处**、数据节指针 **0 处** |

C3 是补的：C2 只扫三小段，扫不到「直接引用第 12 行」这种写法
（`0x4c53c0 + 12*0x34 = 0x4c56d0` 落在三段之外）。补扫后确认没有这种引用。

★ **C2 当场救回一个真站点**：`CardCollection__mark_obtained_and_notify` 的
`mov edx, 0x4c53c4` `0x418e0e` 是**表遍历**，按计数收尾（`cmp ecx, 0x38`）而不是按地址，
骨架不同，被 C1 漏掉。补进 `find_walks()` 后总数从 99 变 100。
**这条审计路径必须留着。**

## C′. 阶段性复审（2026-09-02）—— 「覆盖够不够」从四个方向攻

审计 C 证的是「表的每一处引用都在 100 处里」。但用户问的是另一件事：
**卡牌子系统有没有哪块逻辑绕过了这 100 处、仍然在读旧表？** 分四个方向攻：

### C′1. 从函数名单反推 —— 没有游离的读表者

卡牌子系统 51 个已命名函数里，**9 个**含站点；另有 **4 个**调用非内联的
`TableCardData__get` `0x407d70`（`allocate_new_card`、`AbilityMenu__on_tick`、
`CardShop__pick_weighted_random_offer`、`FUN_00419170`）——函数本体已 patch，等价覆盖。
其余 38 个不碰表：它们要么只用 `card->id` 与对象自身字段，要么用
**别处查表得到的指针**（`zAbilityMenu.__card_ptrs_0xfec`、商店 offer 数组）——
那些指针来自已 patch 的查表，指向新表，行为一致。

**结论：CONFIRMED** —— 不存在「既不含站点、又不调 get、却读表」的函数，
因为 C3 已证 `.text` 里对表区间的引用只有那 100 处。

### C′2. 三种「不经查表也会碰表」的写法 —— 都不存在

| 写法 | 长什么样 | 会落在哪段 | 实测 |
| --- | --- | --- | --- |
| 指针 → 下标 | `sub reg, 0x4c53c0` / `imul`+`div` | 表基段的**非 mov/add/lea** 立即数 | **0 处** |
| 与 NULL 行指针比较 | `cmp reg, 0x4c5f20` | 回退段的 **cmp** | **0 处**（25 处全是 `mov`）|
| 静态存的行指针 | `.data` 里的 `zTableCardData*` | 数据节 4 字节对齐指向表内 | **0 处** |

第二条顺带说明游戏判「查不到」靠的是 `entry->id == 56` 或 `entry->+0x0c == 4`
（[`engine/card/th18/11`](../../../engine/card/th18/11-sentinels-56-57.md) §2），
**不是**比较指针。搬表不会改变这个判定。

### C′3. 有符号比较的隐患 —— 不成立

25 处 END 之后都是 **`jl`（有符号）**。codecave 若落在 ≥ `0x80000000`，
`cmp p, END; jl` 会翻转。核对 PE：`Characteristics = 0x0103`，
**无 LARGEADDRESSAWARE** → 32 位进程用户空间 < `0x80000000`，`VirtualAlloc` 给不出高地址。
**REFUTED（不构成问题）**，但换 build 若加了 LAA 要重看。

### C′4. 与其它 patch 撞车 —— vendor 内 0 处，`base_tsa` 待用户实测

100 处 5–7 字节写入点，任何一处被别的 binhack/breakpoint 覆盖，后应用的那个会
「expected 不匹配 → 静默跳过」。新增 `sites.py conflicts <其它.js>` 做区间交集。

- vendor 里的 ExpHP 5 个 th18 patch（9 个 hackpoint）：**0 处重叠**。
- **`base_tsa`（本 mod 声明的依赖）不在 vendor 里** —— **OPEN**，
  用户需拿装机上的 `<thcrap>/repos/nmlgc/base_tsa/th18.v1.00a.js` 跑一次
  `make conflicts OTHERS=…`。它的断点多挂在文本/字体/存档 I/O，
  撞上查表内联点的概率低，但**必须实测，不接受「概率低」**。

### C′5. 第 1 步刻意**不**覆盖的（这不是漏）

行数仍 58，所以 [`11`](../../../engine/card/th18/11-sentinels-56-57.md) §5 的另外 33 处
边界（字面 56/57、`mgr+0xc84` 数组、`zAbilityMenu.__card_ids`、存档数组）**一处不动**，
它们的语义在 58 行下与香草完全相同。这些是战线 B–E 的事，见
[`../card-rework/PLAN-255-ids.md`](../card-rework/PLAN-255-ids.md)。

## D. 量纲 / 算术

| # | claim | 结论 |
| --- | --- | --- |
| D1 | `58 * 0x34 = 3016`，`3016 / 4 = 754 = 0x2f2` 整除 | **CONFIRMED**（`0x34` 可被 4 整除，`rep movsd` 不会剩尾巴）|
| D2 | 拷贝 3016 字节 = 读 `0x4c53c0`–`0x4c5f88`，**不碰**那两个热全局 | **CONFIRMED** —— 末字节是 `0x4c5f87`，`0x4c5f88` 是全局的第一个字节 |
| D3 | rows=255 时 cave 尺寸 = 拷贝量 + 填充量，不多不少 | **CONFIRMED** —— `3016 + 197 × 52 = 13260 = 0x33cc` = 声明的 `size` |
| D4 | 回退行偏移 `56 × 0x34 = 0xb60` | **CONFIRMED** —— 与 `0x4c5f20 − 0x4c53c0 = 0xb60` 一致 |
| D5 | `<codecave:NAME+OFF>` 的 OFF 是**十六进制** | **CONFIRMED** —— `expression.cpp` `GetCodecaveAddress` → `strtouz(…, 16)`。⚠️ 写成看着像十进制的 `+58` 会被当成 `0x58`。生成器一律输出裸十六进制 |

## E. thcrap 行为核对（都是从源码读的，不是记忆）

| # | claim | 结论 |
| --- | --- | --- |
| E1 | `size` 而无 `code` 的 codecave 合法，默认 READWRITE | **CONFIRMED** —— `binhack.cpp:1594` 只在两者皆无时忽略；access 默认见 `codecave_from_json` 尾部 |
| E2 | `export` 要求 access 是 EXECUTE 或 EXECUTE_READ | **CONFIRMED** —— `binhack.cpp:1544`。所以 init cave 声明 `"access": "RX"` |
| E3 | codecave 之间可互相引用 | **CONFIRMED** —— 第二遍先 `func_add` 记录全部地址，第三遍才渲染 `code` |
| E4 | `*_patch_init` 会被调用 | **CONFIRMED** —— `binhack.cpp:1724` → `plugin.cpp:304` `patch_func_init`；`mod_funcs_t::build` 取 `_patch_` 之后的后缀作 key，`th18_card_table_patch_init` → `init` |
| E5 | ⚠️ `*_patch_init` **早于** binhack 应用 | **CONFIRMED** —— `patch_func_init` 在 `codecaves_apply` 末尾，而 `runconfig.cpp:655-656` 是先 codecaves 后 binhacks。**所以它能用来预填新表，但不能用来验证 binhack 是否都打上了** |
| E6 | 页保护在 `patch_func_init` 之后才设 | **CONFIRMED** —— `codecaves_apply` 的 `VirtualProtect` 循环在 `patch_func_init` 之后，所以初始化时整块还是 `PAGE_EXECUTE_READWRITE`，写得进去 |

## F. 仓库纪律

| # | claim | 结论 |
| --- | --- | --- |
| F1 | 不分发游戏字节 | **CONFIRMED** —— 新表内容**运行时**从用户自己的 exe `memcpy`，patch 里只有地址、原字节和源码 |
| F2 | 不写死 `0x400000` | **CONFIRMED** —— 零售表地址用 thcrap 的 `Rx` 记法（`<Rxc53c0>`，`expression.h:310`：相对模块基址）|
| F3 | 可回滚 | **CONFIRMED** —— 从 run config 的 patch 栈里移除即可；不写存档、不改磁盘上的任何游戏文件 |

## G. OPEN —— 还没解决的

| # | 事项 | 说明 |
| --- | --- | --- |
| G1 | **游戏内未实跑** | 静态审计通过 ≠ 能跑。第 1 步的验收标准见 [`README.md`](README.md) |
| G2 | **全有或全无的门还没做** | E5 否定了原方案里「用 `*_patch_init` 回读站点」的做法。替代设计：新表 58 行之后的行**预填成 NULL 行副本**（休眠数据），由**游戏内断点**在验证过全部 binhack 生效后才写入真数据。第 1 步不需要（行数不变，两表逐字节相同，漏改也没有可观察后果），扩容前必须补上 |
| G3 | 扩容还要动的东西 | 战线 B–E 一条都没做，见 [`../card-rework/PLAN-255-ids.md`](../card-rework/PLAN-255-ids.md) |
| G4 | MSVC 换 build 后骨架是否仍然一致 | 未验证。`make check` 的锚点数会立刻暴露（不是 25 就停） |
