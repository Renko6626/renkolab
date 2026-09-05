# 破损核心（card-expand id 71）—— 设计

> **版本**：TH18 v1.00a（`th18.exe`，imagebase `0x400000`）。本文裸地址默认属该版本；引用其他版本须写成 `th16:0x…`。
> 日期：2026-09-05。状态：用户已定三项（见 §0）。归属：`mods/th18.v1.00a/card-expand/`。
> 引擎一手：[`engine/sht/th18/01`](../../../engine/sht/th18/01-file-layout-and-shooterset-index.md)、
> [`engine/sht/th18/02`](../../../engine/sht/th18/02-shooter-record.md)、
> [`engine/card/th18/03-hooks.md`](../../../engine/card/th18/03-hooks.md) §5。

## 0. 一句话

**装备卡**：带着它就在自机旁边多一颗电球子机；电球每隔一段时间朝**最近的敌人**劈一道闪电。
纯正面效果，「破损」只体现在外观与文案上。

用户已定（2026-09-05）：**闪电追踪最近敌人** / **无负面代价** / **贴图程序生成**。

## 1. 为什么走「真装备卡」而不是自绘

零售装备卡 = `on_power_level_change` 里 `Player__allocate_option` 生成子机 +
`on_tick_shooters` 里按烘死的索引取一组 SHT shooter 开火。此前这条路被两件事挡着，现在都通了：

| 挡路的 | 现状 |
| --- | --- |
| shooter 表存在哪 | ✅ 就在 `pl0X.sht` 的 `+0xe0` 偏移数组里，**尾部 17 个空位可用** |
| 子机 / 子弹只能用零售贴图 | ✅ 两者的脚本都取自 **`ability.anm`** —— 本 mod 每张卡都在重建的那个文件 |
| 卡对象没有 `+0x54` 存子机指针 | ⚠️ 我们的对象是基类 `0x54` 字节，改用 SDK 的 `ce_state()` 私有状态槽 |

换来的是：弹的伤害走引擎自机弹管线（顺带吃黑桃 K 的 `on_bullet_created` 加成）、
子机位置/聚焦位移/开店收起全由引擎管、以后每加一张子机卡只是再占一个空位。

## 2. 数值

| 项 | 值 | 理由 |
| --- | --- | --- |
| 卡 id | `71` | 58–70 已占 |
| `internal_name` | `BROKEN_CORE` | |
| `category` | `2`（装备）| 引擎三分类里的装备 |
| `price_tier` | `8`（240）| 与零售 `*_OP` 子机卡（240）同档 |
| `weight` | `2` | 与本 mod 其它卡一致 |
| 子机偏移 | `0x18`（非聚焦 / 聚焦同值）| 介于 Alice `0x1c` 与 Marisa1 `0x10` 之间 |
| SHT 索引 | `0x17` | 第一个空位 |
| 开火周期 | **150 帧（2.5 s）** | 由 C 的计数器决定，不是 `fire_rate` |
| 每次发数 | 1 | shooter 组内一条 |
| 伤害 | **90** | 参照：Alice 子机弹 6 × 每 5 帧 ≈ 72/s；本卡 90 / 2.5 s = 36/s，约为其一半，换来「不用按射击键也打」|
| 弹速 | `12.0` | 比主炮 24 慢，看得清是一道闪电 |
| 锁敌半径 | `512.0` | 抄 Alice 的搜索半径 `0x4b93b0`（她的**开火**上限 128 太近，本卡不设开火上限）|
| 音效 | `0x46 se_noise` | 电流噪声；填 shooter `+0x24`，引擎自己在出膛时放 |

## 3. 实现

### 3.1 SHT：往四个 `pl0X.sht` 追加一组 shooterset

纯追加，前面一个字节都不动：

1. `sht[0xe0 + 0x17*4] := 文件当前长度 − 0x180`
2. 文件尾接一条 `0x5c` 的 shooter + 4 字节 `0xFFFFFFFF`

shooter 字段（其余全 0）：

```
+0x00 fire_rate  = 1        // 每次调用都发；节奏由 C 掌握（fire_rate 是 int8，做不出 150）
+0x01 start_delay= 0
+0x02 damage     = 90
+0x14 angle      = -π/2     // 兜底：func_on_init 会覆写成瞄准角
+0x18 speed      = 12.0
+0x20 opt_slot   = 1        // 从子机位出膛（tick_shooters 传的是 option 对象，槽号只影响取位方式）
+0x21 mode       = 0
+0x22 anm        = <ability.anm 里的闪电弹脚本号>
+0x24 sfx        = 0x46
+0x2c func_on_init = 5      // 0x4612d0：用 player+0x479cc 覆写 bullet 角度
```

**不变式**（[`sht/th18/01`](../../../engine/sht/th18/01-file-layout-and-shooterset-index.md) §3）：
头部 `+0x02` 必须仍是 40；shooterset 0 的四个 func 字段必须仍是 0（剩下 16 个空位靠 `0 → 0` 幂等活着）。
构建脚本每次都回读校验这两条 + 前 23 组逐字节不变。

### 3.2 C 行为 `native/cards/broken_core.c`

| 槽 | 干什么 |
| --- | --- |
| `on_power_level_change` | `Player__allocate_option(this; this, 0x18, this, 0x18, 电球脚本)` → 指针存 `ce_state()`；同时记下它的 ANM vm id（`card+0x1c` 那份由引擎写，我们只读）|
| `on_load` | 清私有状态里的子机指针（照 `CardReimu1____on_load__2` `0x40aab0`：先调 `on_run_reset`，再清指针）|
| `on_run_reset` | `card+0x50 &= ~2`（照 `CardReimu1__method_4C` `0x40aad0`）+ 清指针 |
| `on_tick_2` | 每帧：① 计时 ② 到点则挑最近敌人、写 `player+0x479cc`、调 `tick_shooters_for_ability_card(option, 0, 0, 0x17)` |

**为什么开火挂 `on_tick_2` 而不是 `on_tick_shooters`**：后者只在按住射击键时广播
（`0x45ea00`），而这张卡该「自己定时打」。`on_tick_2` 是 AbilityManager 侧每帧、菜单/商店里不跑，正合适。
`fire_rate = 1` + `short_timer = 0` ⇒ `0 % 1 == 0` 恒真，所以「调用即开火」，周期完全由 C 的计数器决定。

纯逻辑（计时器状态机 + 选最近目标 + 角度）放 `broken_core_core.c`，主机 `make test-host` 单测；
引擎调用只在 `broken_core.c` 里，走 `sdk.h` 的薄包装。

### 3.3 选目标（照 `0x438cb0` 的规则，自己走链表）

```c
for (node = *(void**)(EnemyManager + 0x18c); node; node = node->next) {
    enemy = node->entry;
    if (*(u32*)(enemy + 0x635c) & 0xc000021) continue;      // 不可锁定
    d2 = dist2(orb, *(float2*)(enemy + 0x1270));
    if (d2 < best) { best = d2; target = enemy; }
}
if (target && best <= 512²) angle = atan2f(ty - oy, tx - ox);
```

不调引擎那个 `0x438cb0`（省一条新的调用约定；规则一样，自己走链表 10 行）。
子机坐标 `option+0x5c` / `+0x60` 是**定点数**，`× 1/128` 变像素。

### 3.4 美术（程序生成，`assets/ability/make_broken_core_art.py`）

| 文件 | 尺寸 | 内容 |
| --- | --- | --- |
| `broken_core/CORE.png` | 128×128 | 电球：青白发光核心 + 一道裂缝 + 环绕电弧；加色混合 |
| `broken_core/BOLT.png` | 128×64 | 闪电弹：横向的锯齿电弧（脚本里按 `func_on_init` 给的角度旋转）|
| `cards/BROKEN_CORE_{max,min}.png` | 256×320 / 64×80 | 卡图：同一支笔画的破损核心，`fit_card.py` 套零售框 |

`ability.anm` 追加：entry `BROKEN_CORE_ORB`（sprite 121）、`BROKEN_CORE_BOLT`（122）；
脚本 88 = 电球常驻（缓慢自转 + 电弧闪烁），脚本 89 = 闪电弹（出膛拉长、拖尾）。

## 4. 风险 / 审计点（AUDIT §U）

| # | 点 | 怎么防 |
| --- | --- | --- |
| U1 | `Player__allocate_option` 的 5 个栈参里**第 1、3 个是 this 自己**（`0x40aae0` 的压栈序）| 原样复刻压栈序，内联汇编 + 注释钉死；别信反编译的形参名 |
| U2 | 12 个子机槽满了返回 NULL | 判空；NULL 时这张卡静默不开火 |
| U3 | sht 追加破坏解析不变式 | 构建脚本回读校验：`+0x02 == 40`、set 0 的 func 全 0、前 23 组逐字节不变 |
| U4 | `fire_rate == 0` 在装备卡路径上除零 | 我们填 1；构建脚本校验 `1 <= fire_rate <= 127` |
| U5 | `on_tick_2` 里 `PLAYER_PTR` / 子机指针为空（菜单、切关）| 逐个判空 |
| U6 | 敌人链表在遍历中被改 | 只在 `on_tick_2`（主线程、EnemyManager tick 之外）读；不缓存 enemy 指针跨帧 |
| U7 | `player+0x479cc` 是共享的瞄准角，Alice 也在写 | 我们只在开火那一帧写、写完立刻开火（Alice 同款用法）；同帧两张卡都开火时后写的赢——可接受（各自的弹在各自的 `func_on_init` 里取值，顺序即写入顺序）|
| U8 | thcrap 能不能替换 `pl0X.sht` | 与 `abcard.anm` 同机制（都走游戏的文件装载）；实跑清单里单列一条 |

## 5. 实跑标志

```
sdk: 71 bound (.on_power_level_change = …, .on_tick_2 = …, .on_load = …, .on_run_reset = …)
broken_core: option allocated (slot ptr …, anm id …)
broken_core: fire #1 at frame 150, target enemy … dist 143.2, angle -1.83
```

体感：自机右侧多一颗电球；每 2.5 s 朝最近的敌人劈一道闪电（有敌人时），打中掉血、听得到电流声；
没有敌人 / 敌人在 512 px 外时不发。过关不消失（装备卡）。商店里进店时电球跟着收起。
