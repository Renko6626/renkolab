# TH18 自机位置与状态计时器 —— `zPlayerInner.field_0` 那 0x50 字节是什么

> **版本**：TH18 v1.00a（`th18.exe`）。本文裸地址默认属该版本；引用其他版本须写成 `th16:0x…`。
> **方法**：一手反编译 `Player__sub_45b170` `0x45B170` 与 `Player__on_tick__body` `0x45BE90`，
> 对照 ExpHP 的 `zPlayer` / `zPlayerInner` 结构体尺寸做闭合核对。
> **可信度**：✅（布局按字节闭合，量纲过常识关）。

## 0. 为什么「TH18 里找不到玩家坐标」

因为它**没有名字**。ExpHP 的 `zPlayer`（0x479d4 字节）把 `inner` 放在 **`+0x620`**，
而 `zPlayerInner` 的第一个成员是 `field_0: char[80]` —— 一个不透明 blob。
**位置就在这个 blob 里**，所以按名字搜 `pos` / `x` / `y` 一无所获，
反编译里也只会看到 `*(float *)(param_1 + 0x620)`。

（TH16 侧有对应的命名是因为那边我们自己反过并落了字段图，见
[`../th16/05-object-field-maps.md`](../th16/05-object-field-maps.md)。）

## 1. 布局（一手，按字节闭合）

| `inner` 内偏移 | 绝对（`player+`）| 类型 | 语义 |
| --- | --- | --- | --- |
| +0x00 / +0x04 / +0x08 | `0x620` / `0x624` / `0x628` | float | **x / y / z（像素）** |
| +0x0c / +0x10 | `0x62c` / `0x630` | int | **x / y 的亚像素定点**（单位 1/128 px）|
| +0x14 .. +0x27 | `0x634` .. `0x647` | `zTimer` | 状态/动画计时器 1（`+0x638` = current）|
| +0x28 .. +0x3b | `0x648` .. `0x65b` | `zTimer` | 状态计时器 2 |
| +0x3c .. +0x4f | `0x65c` .. `0x66f` | `zTimer` | 状态计时器 3 |

`12 + 8 + 3 × 20 = 80 = 0x50` —— **正好填满 `field_0`**，没有余量。

## 2. 证据链

- **① 发现**：`Player__on_tick__body` `0x45BE90` 里同一个 `zPlayer*` 既写
  `Player__repopulate_options_and_notify_cards((int)param_1 + 0x620)`，
  别处又写 `Player__repopulate_options_and_notify_cards((int)&PLAYER_PTR->inner)`
  —— 两种写法指同一地址，故 **`inner` 的偏移 = `0x620`**（与结构体表里 `offset 1568` 一致）。
- **② 发现**：`Player__sub_45b170` `0x45B170`（移动处理）末尾：

  ```c
  player+0x62c += (int)(dx * DAT_004ccbf0);           // 定点累加
  player+0x630 += (int)(dy * DAT_004ccbf0);
  钳位:  x ∈ [-0x5c00, 0x5c00]      y ∈ [0x1000, 0xd800]
  player+0x620 = (float)player+0x62c * SUBPIXEL_TO_PIXEL_1_over_128;   // 0x4b908c
  player+0x624 = (float)player+0x630 * SUBPIXEL_TO_PIXEL_1_over_128;
  ```

- **③ 验证（量纲常识关）**：`0x4b908c` 实读 = **0.0078125 = 1/128**。
  - x 钳位 `±0x5c00` → `±23552 / 128` = **±184 px**。TH18 弹幕区宽 368–384，半宽 184 ✅。
  - y 钳位 `[0x1000, 0xd800]` → `[32, 432] px`。弹幕区高 448，上下各留边 ✅。
  - 又：`Card__death_save_bomb_revive` `0x40A2A0` 与各主动卡的 `c_press` 都把
    `*(undefined8 *)PLAYER_PTR->inner.field_0`（= x,y 一对）+ `field_0 + 8`（= z）
    当坐标传给 ANM VM —— **第三方用法一致**。
- **④ 结论**：**TH18 自机位置 = `player+0x620/0x624/0x628`（float, px），
  权威副本是 `player+0x62c/0x630` 的 1/128 px 定点整数** ✅（TH18 v1.00a）。
  `field_0` 剩下的 0x3c 字节是三个连排的 `zTimer`。
- **⑤ 证据**：`0x45B170`、`0x45BE90`、`0x4b908c`、`0x40A2A0`；
  结构体 `zPlayer.inner @ offset 1568`、`zPlayerInner.field_0 : char[80]`。

## 3. 顺带确认的两个字段

| 字段 | 地址 | 证据 |
| --- | --- | --- |
| 玩家状态机 | `player+0x476ac` | `Player__on_tick__body` 的 `switch`（0–4）|
| 聚焦位 | `player+0x476cc` | `player+0x476cc = INPUT_HELD >> 3 & 1`（`0x45B3FA`）|
| 决死窗口帧数 | `player+0x47908` | `zPlayerInner.num_deathbomb_frames`；`Player__die` 置 8 |

## 4. 为什么 `Player__*` 的反编译里还是 `param_1 + 0x620`

因为**它被故意排除在类型绑定之外**。`tooling/ghidra/bind_types.py` 已经把卡牌那 268 个
函数绑好了 this 类型，但 `Player__*` 在规则文件的 `ambiguous` 里，理由就是本文 §2 的发现：

> **它的 this 有时是 `zPlayer*`，有时是 `zPlayerInner*`**（`inner` 在 `+0x620`）。
> `Player__on_tick__body` 读 `+0x476ac` 走 `zPlayer`；而
> `Player__repopulate_options_and_notify_cards` 的实参是 `&PLAYER_PTR->inner`。
> **整族一刀切必错**，得逐个函数定。

所以要让 `Player__*` 也可读，下一步是**逐函数判定 this 是哪一个**，
再写进 `tooling/ghidra/bindings/th18.v1.00a.json` 的 `overrides`。
在那之前，本文与 `engine/card/th18/` 各篇的伪代码块一律**保留裸偏移**
（写成 `player+0x620`、`card->state(+0x54)`），好直接对回反编译输出。
