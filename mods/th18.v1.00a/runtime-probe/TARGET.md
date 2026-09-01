# TARGET —— runtime-probe 死绑登记

> **版本**：TH18 v1.00a（`th18.exe`，imagebase `0x400000`）。本文裸地址默认属该版本；引用其他版本须写成 `th16:0x…`。

**这份文件回答一个问题：换一个 exe build，我要重取哪些量？**
本探针**只读**——没有 binhack、没有 codecave、不往游戏内存写任何字节，
所以没有「写入点」一节；对应位置换成**读取点**与**签名校验点**。

## 目标二进制

| 项 | 值 |
| --- | --- |
| 游戏 / 版本 | th18 v1.00a |
| exe md5 | `9969cac756098c1da05a81de45437a70` |
| 大小 | 847360 B |
| imagebase | `0x400000` |
| DYNAMICBASE | **无**（`DllCharacteristics=0x8100`）→ 镜像必落 `0x400000` |
| thcrap 版本匹配 | **不依赖**——探针自己按下面两处签名认版本 |

⚠️ 虽然该 exe 无 ASLR，探针仍按 `GetModuleHandleW(NULL)` 取实际基址再加 RVA，
不假设 `0x400000`。这样将来遇到有 ASLR 的 build 不必改逻辑。

## 签名校验点（相当于 binhack 的 `expected`）

两处都在 `.text`，任一不匹配即 `thcrap_plugin_init` 返回 1 自我卸载。

| # | 地址 | RVA | 原字节（16） | 依据 |
| --- | --- | --- | --- | --- |
| A | `0x45b170` | `0x5b170` | `55 8b ec 83 e4 f0 f3 0f 10 1d 74 91 4b 00 83 ec` | `Player__sub_45b170`，移动处理，本探针所有坐标结论的一手来源 |
| B | `0x45caa0` | `0x5caa0` | `83 3d a4 f2 4c 00 00 74 06 b8 01 00 00 00 c3 e9` | `Player__on_tick`，独立第二锚点 |

对账脚本：`native/check_constants.py`（`make check`）——把源码里写死的字节拿去和真 exe 比。

## 读取点

| # | 地址 / 算式 | 类型 | 语义 | 依据 |
| --- | --- | --- | --- | --- |
| 1 | `0x4cf410` | `zPlayer*` | `PLAYER_PTR`，**先解引用再用** | ExpHP `statics.json`（th18.v1.00a） |
| 2 | `player+0x620` / `+0x624` / `+0x628` | float | x / y / z（像素） | [`engine/player/th18/01`](../../../engine/player/th18/01-position-and-state-timers.md) §1 ✅ |
| 3 | `player+0x62c` / `+0x630` | int | x / y 亚像素定点（1/128 px），**权威副本** | 同上 §2② |
| 4 | `player+0x476ac` | int | 玩家状态机（`Player__on_tick__body` 的 switch 0–4） | 同上 §3 |
| 5 | `player+0x476cc` | int | 聚焦位（`INPUT_HELD >> 3 & 1`） | 同上 §3 |

## codecave 调用的引擎函数

**无。** 探针不调用引擎任何函数，不构造栈帧，不触碰 FPU 栈——
`_template/AUDIT-checklist.md` 的 A 节（ABI / 栈平衡，历史上唯一的真 BLOCKER 所在）
对本探针整节不适用。这正是把它选作阶段 0 的理由。

## 依赖的结构偏移

见上表读取点 2–5，全部来自 `zPlayer`（`zPlayer.inner @ +0x620`，`zPlayerInner.field_0 : char[80]`）。

## 运行期自校验（跑起来之后判对错的判据）

探针每行日志自带两个判定，**不用人去比对文档**：

| 判定 | 判据 | 出处 |
| --- | --- | --- |
| `IN-RANGE` | x ∈ [-184, 184]，y ∈ [32, 432] 像素 | 钳位 `±0x5c00` / `[0x1000, 0xd800]` ÷ 128 |
| `ok` / `MISMATCH` | float 坐标 == 定点值 / 128（容差 0.01） | `0x4b908c` 实读 = 1/128 |

两个都绿 = `PLAYER_PTR` 与全部偏移在活进程上成立。任一红 = 我们的映射错了，回 `engine/` 复核。

## 换版本时必须重取

- [ ] 两处签名的地址与原字节（A / B）
- [ ] `PLAYER_PTR` 地址
- [ ] `inner` 在 `zPlayer` 内的偏移（th18 是 `+0x620`；th16 完全不同）
- [ ] `state` / `focus` 的绝对偏移
- [ ] 钳位常量（弹幕区尺寸逐作可能变）→ 自校验判据随之变

可以借的只有：方法论、字段的*语义*、`field_0` 那 0x50 字节的布局形状。
