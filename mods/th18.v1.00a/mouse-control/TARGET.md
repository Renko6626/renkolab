# TARGET —— mouse-control 死绑登记

> **版本**：TH18 v1.00a（`th18.exe`，imagebase `0x400000`）。本文裸地址默认属该版本；引用其他版本须写成 `th16:0x…`。

**这份文件回答一个问题：换一个 exe build，我要重取哪些量？**

对账脚本：`native/check_constants.py`（`make check`）——它同时查源码里的签名和
patch 里的断点声明，两边都跟真 exe 比。**换 build 后先过这一关，再谈跑。**

## 目标二进制

| 项 | 值 |
| --- | --- |
| 游戏 / 版本 | th18 v1.00a |
| exe md5 | `9969cac756098c1da05a81de45437a70` |
| 大小 | 847360 B |
| imagebase | `0x400000` |
| DYNAMICBASE | 无（`DllCharacteristics=0x8100`）→ 镜像必落 `0x400000` |

⚠️ 代码仍按 `GetModuleHandleW(NULL)` 取实际基址再加 RVA，不假设 `0x400000`。

## 写入点

**只有一个地址，而且不是代码**——两条都写 `INPUT_HELD`：

| # | 地址 | 写什么 | 依据 |
| --- | --- | --- | --- |
| 1 | `0x4ca428` | `INPUT_HELD` 的方向位 `0xf0`（**覆盖**，其余位保留） | [`engine/card/th18/04`](../../../engine/card/th18/04-active-cards.md) §1，逐位有证据 |
| 2 | `0x4ca428` | `INPUT_HELD` 的 `0x001`（射击）/ `0x002`（炸弹）/ `0x400`（用卡）（**只 OR，从不清位**） | 同上 |

玩家对象、`.text`、跳转表**一律不写**。钳位/子机轨迹/动画/外力全部由游戏自己完成。

## hook 点（thcrap breakpoint）

| # | 地址 | `expected` | `cavesize` | 函数 | 依据 |
| --- | --- | --- | --- | --- | --- |
| 1 | `0x45b170` | `55 8b ec 83 e4 f0` | 6 | `BP_mouse_move` | `Player__sub_45b170` 入口 |
| 2 | `0x462966` | `e8 55 82 fc ff` | 5 | `BP_mouse_buttons` | `ReplayManager__on_tick__record_replay` 里 `call Input__compute_edges` 那条 |

hook 1 的 `cavesize` = 6 覆盖三条完整指令：`push ebp`(1) + `mov ebp,esp`(2) +
`and esp,-0x10`(3)，都不含相对寻址，挪进 cave 执行等价。

hook 2 的 `cavesize` = 5 正好是那条 `call rel32`。**相对 call 挪进 cave 是安全的**——
thcrap 会修正开头的相对 call/jmp 偏移（`breakpoint.cpp` 的 "Fix relative stuff #1"）。

断点函数返回 1 = 照常执行这段原指令（`breakpoint.h:26-30`）。

**断点名 → 函数名**：JSON 里的 key `mouse_move` → thcrap 找导出的 `BP_mouse_move`
（`breakpoint.cpp:335`）。找不到时记一行日志并**跳过该断点**（`binhack.cpp:39`），不崩。

## 版本守卫签名

`thcrap_plugin_init` 里逐字节校验，不匹配即返回 1 自我卸载（thcrap 会 `FreeLibrary`）。

| # | 地址 | RVA | 原字节（16） | 是什么 |
| --- | --- | --- | --- | --- |
| A | `0x45b170` | `0x5b170` | `55 8b ec 83 e4 f0 f3 0f 10 1d 74 91 4b 00 83 ec` | `Player__sub_45b170`，也是 hook 点 |
| B | `0x45caa0` | `0x5caa0` | `83 3d a4 f2 4c 00 00 74 06 b8 01 00 00 00 c3 e9` | `Player__on_tick`，独立第二锚点 |

## 读取点

| # | 地址 / 算式 | 类型 | 语义 | 依据 |
| --- | --- | --- | --- | --- |
| 1 | `0x4cf410` | `zPlayer*` | `PLAYER_PTR`，用于与 ECX 交叉核对 | ExpHP `statics.json` |
| 2 | `0x4ccdf0` + `0x58` | HWND | `zSupervisor.main_window` | ExpHP `type-structs-own.json` |
| 3 | `0x4ca428` | uint32 | `INPUT_HELD`（读低速位 `0x008`；另见写入点） | `engine/card/th18/04` §1 |
| 4 | `player+0x62c` / `+0x630` | int | x / y 亚像素（1/128 px），**权威副本** | [`engine/player/th18/01`](../../../engine/player/th18/01-position-and-state-timers.md) §2② |
| 5 | `player+0x4779c` | uint | flags；`& 0x180` != 0 时游戏走入场/死亡动画分支，我们放行 | `0x45b170` 首行分支 |
| 6 | `player+0x477b4` / `+0x477b8` | int | 直线速度：非低速 / 低速 | `0x45b170` 速度选择四分支 |
| 7 | `player+0x477bc` / `+0x477c0` | int | 斜向速度：非低速 / 低速（v1 未用，见 [`AUDIT.md`](AUDIT.md) D 节） | 同上 |
| 8 | `player+0x477ec` | float | 速度倍率 | `0x45b170` 末段 `* *(float*)(p+0x477ec)` |
| 9 | `player+0x476cc` | int | 低速位。**v1 未用**——它在 hook 点之后才被写入，读到的是上一帧 | 同上 |

`this` 从 `regs->ecx` 取（`Player__sub_45b170` 是 `__fastcall` 单参），并与读取点 1 交叉核对。

## 移动公式（本 mod 的全部依据）

```
dir_idx = 八向分支(INPUT_HELD & 0xf0)                      → player+0x4793c
dirvec  = DAT_004b7040[dir_idx]        实读 = 纯 ±1,未归一化
speed   = focus ? (dir<5 ? +0x477b8 : +0x477c0)
                : (dir<5 ? +0x477b4 : +0x477bc)
step    = (dirvec*speed - (int)(+0x477f0 * -128.0)) * (+0x477ec)
player+0x62c += (int)(step * 1.0)
钳位 x∈[-0x5c00,0x5c00]  y∈[0x1000,0xd800]
player+0x620 = 亚像素 * (1/128)
```

实读常量：`0x4b7040` 表 = `(0,0)(0,-1)(0,1)(-1,0)(1,0)(-1,-1)(1,-1)(-1,1)(1,1)`，
与八向分支逐条对上；`0x4b9464` = `-128.0`；`0x4b908c` = `1/128`；`0x4ccbf0` = `1.0`。

## 弹幕区几何

| 量 | 值 | 来源 |
| --- | --- | --- |
| 虚拟屏幕 | 640×480 | ExpHP `anm/stages-of-rendering.md`：自机/弹幕/激光/道具画在 surface 0，坐标空间恒为 640×480 |
| 游戏区 | `{x:32, y:16, w:384, h:448}` | 同上（th11 sprite75/76、th14 sprite89） |
| 缩放 | 1x / 1.5x / 2x → 640×480 / 960×720 / 1280×960 | 同上，由一个 ANM 脚本 `scale()` 一次做掉 |
| 游戏坐标原点 | x 以游戏区水平中心（虚拟 224）为 0；y 以游戏区顶边（虚拟 16）为 0 | 由钳位反推 |

**★ 尺寸 384×448 由 th18 自己的钳位常量独立佐证**，不是借来的：

| 钳位（th18 一手） | 游戏坐标 | 640 空间 | 游戏区边 | 余量 |
| --- | --- | --- | --- | --- |
| x ≥ `-0x5c00` | -184 | 40 | 32 | 8 px |
| x ≤ `0x5c00` | +184 | 408 | 416 | 8 px |
| y ≥ `0x1000` | 32 | 48 | 16 | 32 px |
| y ≤ `0xd800` | 432 | 448 | 464 | 16 px |

四条边全部落在 384×448 内、左右余量对称 8px —— 只有游戏区确实是 384×448 时才成立。
🟡 仍是借来的只有**屏幕原点 `(32,16)`**（ExpHP 的 th11/th14 证据）；错了的症状是
自机整体偏一个固定量，改 `th18.h` 的 `PLAYFIELD_CX`/`PLAYFIELD_TOP` 即可。

## 换版本时必须重取

- [ ] 两个 hook 点的地址、`expected`、`cavesize`（按新的指令边界重取，不要照抄 6/5）
- [ ] 两处版本守卫签名
- [ ] `PLAYER_PTR` / `INPUT_HELD` / `SUPERVISOR` 三个全局地址
- [ ] `zSupervisor.main_window` 的结构内偏移
- [ ] `zPlayer` 的全部偏移（`inner` 位置逐作不同，th18 是 `+0x620`）
- [ ] `INPUT_HELD` 的位义（方向 `0xf0`、低速 `0x008`、射击 `0x001`、炸弹 `0x002`、用卡 `0x400` 逐作可能变）
- [ ] 钳位常量与弹幕区几何（改了则坐标变换与自校验判据同时作废）

可以借的只有：方法论、字段的*语义*、移动公式的**形状**。
