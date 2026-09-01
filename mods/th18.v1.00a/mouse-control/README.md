# mouse-control —— TH18 鼠标控制

> **版本**：TH18 v1.00a（`th18.exe`，imagebase `0x400000`）。本文裸地址默认属该版本；引用其他版本须写成 `th16:0x…`。

用鼠标操自机：光标在哪，自机往哪走。**F9** 开关。

实现方式是**合成输入**——每帧按光标方位算出「该按哪个方向键」，写进 `INPUT_HELD`
的方向位，剩下全部交给游戏自己的移动代码。所以钳位、子机跟随、倾斜动画、
速度倍率、外力位移**一个都不用我们操心**，它们本来就是那条路径的一部分。

**玩家对象零写入**：整个 mod 只写 `INPUT_HELD` 一个 dword。

## 装法

两件套（本 mod 自带 DLL，见 [`AUDIT.md`](AUDIT.md) 的架构说明）：

| 放哪 | 什么 |
| --- | --- |
| `<thcrap>/bin/th18_mouse.dll` | 插件（只从 `bin` 加载，`init.cpp:333`） |
| patch 栈里加上 `patch/` 这个目录 | 断点声明（地址 / `expected` / `cavesize`） |

本地测试不用架服务器：run config（`<thcrap>/config/*.js`）里给 patch 数组加一项，
`archive` 指向 `patch/` 的路径（相对 thcrap 根或绝对都行），然后
`thcrap_loader.exe <你的config>.js th18`。`patch.js` 里已经设了 `"update": false`，
thcrap 不会去同步一个不存在的远端。细节见 [`../../thcrap-platform.md`](../../thcrap-platform.md) §6.2。

## 用法

| 操作 | 效果 |
| --- | --- |
| **F9** | 开 / 关鼠标控制（只在游戏窗口是前台时响应）。开启时光标隐藏 |
| 移动鼠标 | 自机朝光标走；光标移出弹幕区则停在对应的墙上 |
| **左键** | 射击（等同 Z）|
| **右键** | 炸弹（等同 X）|
| **中键** | 用卡（等同 C）|
| Shift | 照常低速。**死区随之变小**，低速下定位明显更准 |
| Z / X / C / D | 照常可用 |

- **方向**：开启期间键盘方向键失效（每帧被覆盖）。关掉即恢复。
- **按键**：只叠加、不清位，所以键盘 Z/X 与鼠标左右键**同时有效**。
- 按键同样受 F9 管；且只在游戏是前台时接管，alt-tab 出去点别的窗口不会走火。

## 怎么算成功

先看 `<游戏目录>/th18_mouse.log`（目录只读时退到 `%TEMP%`）：

```
[guard] 两处 .text 签名匹配,确认 th18.v1.00a。
BP_mouse_move 就绪(F9 开关鼠标控制)
```

再看 thcrap 日志里有没有 `[Plugin] th18_mouse.dll: initialized and active`。
若是 `ERROR: function 'BP_mouse_move' not found!` → DLL 没放进 `bin` 或版本守卫拒绝了。

进关卡按 F9，四条验收：

| # | 看什么 | 通过 | 不通过说明什么 |
| --- | --- | --- | --- |
| 1 | 自机朝光标移动并停在光标附近 | 坐标变换正确 | 见下「偏了怎么办」 |
| 2 | 按住 Shift 时定位明显更准 | 死区随合法步长缩小，速度读对了 | `+0x477b4/b8` 读错 |
| 3 | 子机跟着自机走、自机有左右倾斜动画 | 合成输入路线成立（这些都是游戏自己做的） | 说明我们其实没走输入路径 |
| 4 | 光标移出弹幕区时自机贴墙不抖 | 目标钳位生效 | 目标没被钳到 `±0x5c00` / `[0x1000,0xd800]` |

**静止时的轻微抖动是设计内的**：游戏每帧只能朝八个方向之一移动**整整一步**，
所以够不上一步时我们不发方向（死区）。自机会停在光标周围约一步的范围内，
低速下这个范围很小。真要压到像素级，得加出口 hook 补残差——见下。

## 没反应？按这张表查

两个都不报错、不崩溃，**什么都不发生**——所以先看日志停在哪一行。

| 日志最后一行 | 说明 | 怎么办 |
| --- | --- | --- |
| `BP_mouse_move 就绪…`，之后没有任何 `[diag]` | **断点没挂上**。最常见的原因是只把 DLL 放进了 `bin`，忘了把 patch 加进 run config | 见上「装法」：patch 目录 + run config 的 `patches` 数组里加 `{"archive": "…"}` |
| 有 `[diag] BP_mouse_move 首次触发`，但 F9 无效 | 断点通了。看下一条 `[diag]` 说停在哪个提前返回 | 按那行打出来的实际值排查 |
| `[diag] ecx=… 与 PLAYER_PTR=… 不等` | `this` 取错了 | 已知原因见 [`AUDIT.md`](AUDIT.md) §1.5 #2 |
| `[diag] 客户区 …x… 不是 4:3` | 全屏黑边等，换算不成立，已自动停用 | 改窗口模式 |
| 有 `[diag] 首次生效 …` 但手感不对 | 断点与坐标链路都通了 | 那行给出 client 尺寸 / 光标 / 目标 / 当前位置 / 步长，对着看 |

**注意**：断点没挂上时，thcrap 自己的日志**也不会**报 `function not found`——
根本没有断点需要解析，所以不报错是正常的，别把它当成「一切正常」。

## 偏了怎么办

坐标变换是：客户区像素 → ÷缩放 → 640×480 虚拟像素 → 减去游戏区原点 → ×128 亚像素。

游戏区在 640×480 空间里是 `{x:32, y:16, w:384, h:448}`
（ExpHP `anm/stages-of-rendering.md`：自机/弹幕/道具都画在 640×480 的 surface 上，
最后由一个 ANM 脚本整体缩放 1x / 1.5x / 2x）。**尺寸 384×448 由 th18 自己的钳位常量
独立佐证**（[`TARGET.md`](TARGET.md) §几何），只有屏幕原点 `(32,16)` 是从 ExpHP 的
th11/th14 借来的 🟡。

所以万一 TH18 不一样，症状是**自机停的位置整体偏一个固定量**——改
`native/th18.h` 里的 `PLAYFIELD_CX` / `PLAYFIELD_TOP` 重编即可，不会崩。

窗口客户区不是 4:3 时（全屏黑边等）换算不成立，mod 会**永久停用并记一行日志**，
不给一个偏掉的结果。v1 只保证窗口模式。

## 编译

需要 llvm-mingw（msvcrt 变体，Linux 宿主，无需 sudo）：

```bash
cd ~/Tools
curl -sSLO https://github.com/mstorsjo/llvm-mingw/releases/download/20260826/llvm-mingw-20260826-msvcrt-ubuntu-22.04-x86_64.tar.xz
tar xf llvm-mingw-20260826-msvcrt-ubuntu-22.04-x86_64.tar.xz
```

```bash
cd native
make check     # 死绑量对账:exe md5、两处签名、patch 里的 addr/expected/cavesize
make           # 出 th18_mouse.dll
make verify    # 位数 / 导出表 / 依赖 / x87 自检
```

`make verify` 四项都不是形式，错了都会**静默**失效：

| 项 | 错了会怎样 |
| --- | --- |
| `PE32 … Intel 80386` | 位数不符的插件被 thcrap 拒绝（`plugin.cpp:355`） |
| 导出表是**无装饰**名 | thcrap 在 `LoadLibrary` 前先扫导出表找 `thcrap_plugin_init`（`pe.cpp:88`）；`__stdcall` 不经 `.def` 会变成 `_thcrap_plugin_init@0`，被判为「不是插件」 |
| 依赖只有 kernel32/user32/msvcrt | 多余依赖 = 用户机器上可能缺的东西 |
| **x87 自检** | 断点跑在游戏线程上下文里，未平衡的 FPU 栈会在**别处**崩。所以编译带 `-mfpmath=sse -msse2`，并反汇编我们自己的目标文件确认零条 x87 |

## 目录

```
mouse-control/
├── README.md              # 你在这
├── TARGET.md              # ★ 死绑登记:hook 点 / 读取点 / 换版本要重取什么
├── AUDIT.md               # 对抗审计 + 实跑记录
├── native/
│   ├── th18.h             ★ 全部死绑量集中一处
│   ├── thcrap_bp.h        thcrap 断点 ABI 的最小复刻(x86_reg_t)
│   ├── dll_main.c         入口 / 版本守卫 / 日志
│   ├── bp_mouse.c         BP_mouse_move —— 全部逻辑
│   ├── th18_mouse.def     导出无装饰名
│   ├── Makefile
│   └── check_constants.py
└── patch/
    ├── patch.js           id / title / dependencies / update:false
    ├── files.js           crc32 清单(分发用)
    └── th18.v1.00a.js     ★ breakpoints: mouse_move → BP_mouse_move
```

## 还没做

- **残差补正**：出口再挂一个 hook，把八向落点与光标之间的残差补上，可得像素级定位。
  是**独立的一次写**，不影响已验通的部分。等实跑觉得不够准再说。
- **切卡 `0x800`**：还没映射（键盘 D 照常）。要的话一行的事。
- **全屏**：见上，客户区非 4:3 时自动停用。
