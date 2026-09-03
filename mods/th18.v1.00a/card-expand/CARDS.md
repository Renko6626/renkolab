# CARDS —— 已实装的新卡一览

> **版本**：TH18 v1.00a（`th18.exe`，imagebase `0x400000`）。本文裸地址默认属该版本；引用其他版本须写成 `th16:0x…`。
> 人看的目录。**数据的真相在 `patch/th18/cards.js`，行为的真相在 `native/cards/*.c`**；本表每加一张卡补一行。
> id 58–254 可用（≤ 71 张，[`DATA.md`](DATA.md) §4）。状态：✅ 实跑通过 / 🔧 待实跑 / 💡 设计中。

## 黑桃（原型：德州扑克・皇家同花顺）

| id | 名字 | 效果 | 实现（槽 / 事件） | 文件 | 状态 |
| --- | --- | --- | --- | --- | --- |
| 58 | 黑桃 10 | 从道具获得的金钱 +10％（每第 10 个金钱道具多给 1；确定性计数，replay 安全）| `on_item_money` | `s10.c` | 🔧 |
| 59 | 黑桃 J | 移动速度 +10％ | `on_tick_2` 写移速倍率 `player+0x477ec` | `sj.c` | 🔧 |
| 60 | 黑桃 Q | 道具自动回收范围大幅增加（吸引半径 70 → 250）| `on_load` 写玩家回收四参（抄 Nitori）| `sq.c` | 🔧 |
| 61 | 黑桃 K | 自机弹伤害 +10％ | `on_bullet_created` 改 `bullet+0x9c`（抄 Momoyo）| `sk.c` | 🔧 |
| 62 | 黑桃 A | Miss 后的无敌时间 +50％（280 → 420 帧）| `on_tick_2` 识别复活计时器 {279,280} | `sa.c` | 🔧 |

**卡图**：五张用标准英式牌面（Wikimedia Commons，Dmitry Fomin，CC0；`assets/cards/_src/english_pattern/`，`fit_card.py` 出图），sprite 118/119 … 126/127。

🔧 **皇家同花顺**（`cards/royal.c`，五张共用 `.ctor`）：买到第五张黑桃时触发一次——金钱 +800、残机 +2（上限先 +1 钳 7，照 CardLife）、bomb +2（同法照 CardBomb）。判定：ctor 时其余四张已在 `owned[]`（初始携带不算，只有买齐才算）。AUDIT O26。

## 方片

| id | 名字 | 效果 | 实现（槽 / 事件） | 文件 | 状态 |
| --- | --- | --- | --- | --- | --- |
| 65 | 方片 2 | 商店一次性购买：买下后金钱翻倍（先扣购买价再翻倍；钱不够用火力补差价时结果为 0）；本身不进卡组 | `ctor` 里 `MONEY = 2·M − price`（ctor 先于扣款），`MONEY_TOTAL += 增量`，返回 1 当场销毁 | `d2.c` | 🔧 |

## 致敬・游戏王

| id | 名字 | 效果 | 实现（槽 / 事件） | 文件 | 状态 |
| --- | --- | --- | --- | --- | --- |
| 63 | 强欲之壶 | 购买时立刻获得两张随机卡牌（商店随机池的规则：未拥有、本关可用、按权重）；本身不进卡组 | `ctor` 里 `pick_weighted_random_offer` ×2 → `allocate_new_card(mode 2)`，返回 1 当场销毁（即时卡）| `pot.c` | 🔧 |

## 致敬・UNO

| id | 名字 | 效果 | 实现（槽 / 事件） | 文件 | 状态 |
| --- | --- | --- | --- | --- | --- |
| 64 | 反转牌 | 主动（C 键）：场上所有子弹速度方向反向；充能 60 s。卡图 UNO 反转牌（`fit_card.py`，sprite 128/129）| 第一张主动卡：`active_recharge = 3600`，`on_activate` 扫子弹池翻 `velocity` 与 `angle`（不动激光），并 `ce_anm_spawn` 起 `ability.anm` script68 亮牌（卡图副本绕 Y 轴一圈）| `reverse.c` | 🔧 |

## 约定

- **即时卡**（买了就生效、不进卡组）：`ctor` 或 `dtor` 施加效果后 `return 1`（零售 EXTEND / 六文钱同款，`02-lifecycle.md` §3）。
  这种卡 `deck_visible: 0`（编成里不列，初始携带不调 ctor 会变成死卡）、`repeatable: 1`（可再刷出）。
- 「随机」一律走游戏自己的 RNG 或确定性计数，不引入自己的随机源（replay）。
- 主动卡：`category: 0`，`active_recharge` 给帧数（零售瞬发卡 20–60 s），`on_activate` 返回 0 瞬发 / 1 持续。
- 文案不能含 ASCII `%`，用 `％`。
