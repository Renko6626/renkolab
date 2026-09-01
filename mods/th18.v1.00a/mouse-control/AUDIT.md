# AUDIT —— mouse-control

> **版本**：TH18 v1.00a（`th18.exe`，imagebase `0x400000`）。本文裸地址默认属该版本；引用其他版本须写成 `th16:0x…`。
> 对照 [`_template/AUDIT-checklist.md`](../../_template/AUDIT-checklist.md)。
> 状态：**实跑通过**（2026-09-01，用户的 Windows 机器）。见 §4。

## 0. 架构上的一次有意识例外

[`mods/thcrap-platform.md`](../../thcrap-platform.md) §5 的纪律是「DLL 数量不得随
mod 数量增长」。**本 mod 自带 DLL（路线 C），是对该纪律的例外**——用户侧另有
游戏侧管理器统管多个 DLL，取施工便利。记在这里而不是悄悄破例：将来若管理器不再
兜底，这个 mod 的 `BP_mouse_move` 应当并进共享 DLL，patch 侧一个字都不用改
（断点按名字绑定，DLL 叫什么无所谓）。

## 1. 逐节结论

### A. ABI / 栈平衡

- **CONFIRMED** 调用约定匹配：`BreakpointFunc_t` 是
  `size_t (TH_CDECL *)(x86_reg_t*, json_t*)`（`breakpoint.h:33`），我们声明为
  `size_t __cdecl BP_mouse_move(x86_reg_t*, void*)`。cdecl 由调用方清栈，无 `RET imm` 问题。
- **CONFIRMED** 返回值语义：返回 1 = 执行被挪进 cave 的原指令（`breakpoint.h:26-30`）。
  本模块**所有**出口都返回 `BP_EXEC_ORIGINAL`，从不改 `regs->retaddr`，即不改变任何控制流。
- **CONFIRMED（一度写错，已在实跑中修正）** `x86_reg_t` 布局：
  `eflags,edi,esi,ebp,esp,ebx,edx,ecx,eax,retaddr`（`expression.h` 结构体开头到 `:158`）——
  x86 上是 **pushfd + pushad** 帧 + 返回地址。我们只读 `ecx`。
  ⚠️ **第一版漏了开头的 `eflags`**，整体错位 4 字节，`regs->ecx` 实际读到的是 `EDX`，
  于是 `this` 永远对不上、鼠标控制全程静默失效（详见 §1.5）。
- **CONFIRMED** 目标函数是 thiscall：调用点 `0x45c0ca` 是 `8b cf`（`mov ecx,edi`），
  紧接 `0x45c0cc` 的 `e8 9f f0 ff ff`（`call 0x45b170`）→ ECX = `this`。
- **CONFIRMED** 不调用引擎任何函数、不构造 cave、不手写机器码 → 栈平衡、寄存器保存、
  `add esp` 那一整类问题（历史上唯一的真 BLOCKER）在这里不存在。
- **CONFIRMED ★ 无 x87**：断点跑在游戏线程上下文里，未平衡的 FPU 栈会在别处崩。
  编译带 `-mfpmath=sse -msse2`，且 `make verify` 反汇编**我们自己的目标文件**
  确认零条 x87 指令（不看 msvcrt，它的 printf 内部有 x87 但与我们无关）。
  SSE 寄存器在 MSVC x86 下全是 caller-saved，可以随便用。
- **OPEN（已接受）** `rk_log()` 走 `vfprintf`，msvcrt 内部会用 x87。它自己平衡栈，
  且只在 **F9 切换**和**永久停用**两条路径上调用（每次会话个位数次），常规每帧路径
  一次都不调。接受。

### B. 写入点

- **CONFIRMED** 全 mod **只写一个地址**：`INPUT_HELD` `0x4ca428`。
  hook 1 覆盖方向位 `0xf0`（保留其余位），hook 2 只 OR 上 `0x001`/`0x002`。
  玩家对象、`.text`、跳转表一律不写。
- **CONFIRMED** `expected` 与 exe 逐字节核对：`native/check_constants.py` 直接读
  `patch/th18.v1.00a.js` 拿去和真 exe 比，2026-09-01 实跑通过。
- **CONFIRMED** `cavesize` = 6 = `expected` 的字节数，且正好是三条完整指令
  `push ebp`(55) + `mov ebp,esp`(8b ec) + `and esp,-0x10`(83 e4 f0)。
  三条都不含相对寻址 → 挪进 cave 执行等价。对账脚本也会检查
  `cavesize == len(expected)`，防「挪走的和校验的不是同一段」。
- **CONFIRMED** 每帧不累积：`INPUT_HELD` 每帧由游戏从原始来源 `DAT_004ca210` 重写
  （`engine/card/th18/04` §1），我们的写入活不过一帧。
- **CONFIRMED（原 OPEN 已解决）** 一帧内的输入顺序已一手反出。
  `Input__compute_edges` `0x42abc0` 只有两个调用点，都在 ReplayManager 的 on_tick 里；
  录制那条 `ReplayManager__on_tick__record_replay` `0x462940` 的结构是：

  ```c
  _INPUT_HELD_PREV = INPUT_HELD;
  INPUT_HELD = (uint)DAT_004ca210;   // 原始输入
  Input__compute_edges();            // ← 0x462966，上升沿在这里算
  ...
  FUN_00463060(chunk, INPUT_HELD, INPUT_PRESSED, INPUT_RELEASED);  // 写进 replay
  ```

  推论有三：
  1. **边沿早于 `Player__on_tick` 算完**。所以 hook 1 写的方向位**不会**产生假的
     `INPUT_PRESSED` 边沿——原先担心的菜单乱跳不会发生。
  2. 炸弹读 `INPUT_PRESSED & 2`（上升沿），因此按键**必须**在 `0x462966` 之前注入，
     这决定了 hook 2 的位置（不是随便挑的）。
  3. 记录 replay 的 `0x463060` 在注入点之后 → 鼠标输入会一致地录进录像；
     且这是**录制**那条 on_tick，回放走 `0x462a50`，我们碰不到 → 看录像时自动失效。
- **CONFIRMED** hook 2 的 `cavesize` = 5 正好是那条 `call rel32`（`e8 55 82 fc ff`
  → `0x42abc0`）。相对 call 挪进 cave 安全：thcrap 会修正开头相对 call/jmp 的偏移
  （`breakpoint.cpp` 的 "Fix relative stuff #1"）。
- **CONFIRMED** 按键位只 **OR**、从不清位 → 键盘 Z/X 与鼠标左右键同时有效，
  且我们不可能「按住不放」（不按就不 OR，下一帧游戏本来就会用原始输入重写 `INPUT_HELD`）。
- **CONFIRMED** 按键受 `g_on`（F9）与前台窗口双重门控：alt-tab 出去点别的窗口不会走火。

### C. 偏移与内存安全

- **CONFIRMED** 每个偏移都能回指一手文档，逐条列在 [`TARGET.md`](TARGET.md) 读取点表。
- **CONFIRMED** 全部读取落在对象内：最大偏移 `+0x477ec` < `zPlayer` 尺寸 `0x479d4`。
- **CONFIRMED** `this` 双重校验：取自 `regs->ecx`（`__fastcall` 单参），并与全局
  `PLAYER_PTR` `0x4cf410` 比对；不等即放行。挂错地方时不会去解引用一个野值。
- **CONFIRMED** 空指针：`p` 为 NULL、`hwnd` 为 NULL 或 `IsWindow` 为假，均放行。
- **CONFIRMED** 除零：`cw <= 0 || ch <= 0` 时放行。
- **CONFIRMED** 溢出：坐标换算与死区比较全部用 `long long` 中间量。
  最坏量级 `ay * TAN225_DEN` ≈ 4.2e12，远在 int64 内。
- **CONFIRMED** 无分配、无循环、无字符串处理 → 无 UAF、无越界、无死循环。
- **CONFIRMED** 线程：断点只在游戏线程上跑，全部状态是该线程私有的静态变量，无竞态。

### D. 量纲 / 常识关

- **CONFIRMED** 坐标变换过了**独立佐证**关：384×448 的游戏区尺寸由 th18 自己的钳位
  常量反推得到，与 ExpHP 的 sprite 定义吻合（[`TARGET.md`](TARGET.md) §弹幕区几何）。
  这不是「拿社区数据当事实」，是两条独立证据交叉对上。
- **CONFIRMED** 死区判据量纲正确：`|Δ|² < S²`，两边都是亚像素平方。
- **OPEN（已接受）** 死区用的是**直线**速度 `+0x477b4/b8`，斜向移动时游戏实际的
  合速度是 `斜向速度 × √2`（方向向量是纯 ±1，未归一化）。若 ZUN 令
  斜向 = 直线/√2 则两者相等，我们的 S 精确；否则斜向的死区略有偏差。
  后果仅是斜向时多走/少走不到一步，**不会崩也不会失控**。
  想收紧就按 `dir` 选 `+0x477bc/c0`，等实跑看手感再定。
- **CONFIRMED** 八向量化的扇区边界用 `tan(22.5°)` 的整数比 `414214/1000000`，
  三个分支（纯水平 / 纯垂直 / 斜向）覆盖完整且互斥。
- **CONFIRMED** y 轴方向：游戏 y 向下（顶 32、底 432），故 `dy > 0` 按「下」`0x020`；
  与 `0x45b170` 的 `INPUT_HELD & 0x10 → dirvec (0,-1)` 一致。

### E. 收尾

- **CONFIRMED** 产物 `PE32 executable (DLL) (GUI) Intel 80386`，依赖仅
  `KERNEL32` + `USER32` + `msvcrt`。
- **CONFIRMED** 导出表是**无装饰名** `thcrap_plugin_init` / `th18_mouse_mod_exit` /
  `BP_mouse_move`。这是硬关卡：thcrap 在 `LoadLibrary` **之前**就先扫 PE 导出表
  （`pe.cpp:88`），装饰成 `_thcrap_plugin_init@0` 会被**静默**判为「不是插件」。
- **CONFIRMED** 位数匹配（`plugin.cpp:355` 拒绝位数不符的插件）。
- **CONFIRMED** 版本守卫可自我卸载：两处 `.text` 签名任一不匹配即返回 1，
  thcrap `FreeLibrary` 并记 `not used for this game`（`plugin.cpp:352-357`）。
  此时断点也找不到 `BP_mouse_move`，thcrap 记一行 `function not found` 并**跳过**
  （`binhack.cpp:39`）——不崩、不影响 patch 栈里别的补丁。
- **CONFIRMED** 可还原：删掉 `bin/th18_mouse.dll` + 从 patch 栈移除，无残留、无需回滚字节。
- **CONFIRMED** 加载顺序：插件在 `init.cpp:333` 加载，hackpoint 在
  `thcrap_init_binary()`（`init.cpp:362`）才应用 → `BP_mouse_move` 一定先于断点解析注册。
- **CONFIRMED** 卸载顺序：`ExitDll()` 先 `mod_func_run_all("exit")` 再 `plugins_close()`
  （`init.cpp:459-460`），导出的 `th18_mouse_mod_exit` 会在 `FreeLibrary` 前跑。
- **CONFIRMED —— 游戏内实跑通过**（2026-09-01，见 §4）。经历了 §1.5 的两个问题后跑通。

## 1.5 实跑中发现并修正的问题

按 `METHOD.md`，写错的结论要留痕而不是抹掉。

| # | 现象 | 根因 | 处置 |
| --- | --- | --- | --- |
| 1 | 插件加载、守卫通过，但按 F9 与任何操作都无反应，日志停在 init | **只放了 DLL，没把 patch 加进 run config** → 没有断点声明 → `BP_mouse_move` 从未被调用（它是我们唯一每帧跑的代码，F9 也在它内部轮询） | 文档补排查表；注意此时 thcrap 日志也**不会**报 `function not found`，因为根本没有断点需要解析 |
| 2 | 断点触发了，但 `ecx` 与 `PLAYER_PTR` 永远不等，静默提前返回 | **`x86_reg_t` 复刻漏了开头的 `eflags` 字段**，整体错位 4 字节，`regs->ecx` 读到的是 `EDX` | 补上 `eflags`。教训写进 `native/thcrap_bp.h` 的注释：比对结构体必须从第一行读起，不要从文件中段读起 |

两个都属于「**不报错、不崩溃、什么都不发生**」的类型 —— 这正是当初在
`BP_mouse_move` 里埋一次性诊断的价值：第二个问题靠一行
`[diag] ecx=… 与 PLAYER_PTR=… 不等` 直接定位，没有靠猜。

## 2. 其余已知的小口子

| 事项 | 后果 | 处置 |
| --- | --- | --- |
| 屏幕原点 `(32,16)` 是 ExpHP th11/th14 借来的 🟡 | 自机整体偏一个固定量 | 改 `th18.h` 的 `PLAYFIELD_CX`/`PLAYFIELD_TOP` |
| 激活时离开关卡，光标仍隐藏 | 观感 | F9 关掉即恢复；不做自动判断以免闪烁 |
| 激活期间键盘方向键被覆盖 | 设计如此 | 已在 README 写明 |
| `GetAsyncKeyState(&1)` 的「自上次调用以来」位是进程内共享的 | 若别的插件也查 F9，可能吃掉边沿 | 低风险；出现漏键再换 `GetKeyState` 自己做边沿 |

## 3. 产物

| 项 | 值 |
| --- | --- |
| 文件 | `native/th18_mouse.dll`（构建产物，不入库） |
| 导出 | `thcrap_plugin_init` / `th18_mouse_mod_exit` / `BP_mouse_move` / `BP_mouse_buttons` |
| 工具链 | llvm-mingw 20260826 msvcrt 变体，clang 23.1.0，target `i686-w64-windows-gnu` |
| 复现 | `cd native && make check && make && make verify` |

## 4. 实跑记录

> 跑完请把结果填进来——**包括失败与崩溃**。四条验收判据见 [`README.md`](README.md)。

| 日期 | 环境 | 加载 | 判据 1 朝光标 | 判据 2 低速更准 | 判据 3 子机跟随+倾斜 | 判据 4 贴墙不抖 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-09-01 | Windows | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | 守卫通过、断点触发确认；因 §1.5 的两个问题未走到生效路径 |
| 2026-09-01 | Windows（修正 `x86_reg_t` 后） | ✅ | ✅ | ✅ | ✅ | ✅ | 用户报告**一切正常**。⚠️ 四条判据未逐条单独回报，此处按整体正常记；若后续发现某条不成立，回来改这一行 |
| 2026-09-01 | Windows（加入鼠标按键后） | ✅ | ✅ | ✅ | ✅ | ✅ | 左键射击 / 右键炸弹实跑正常。中键→用卡为同批加入，**尚未单独确认** |
