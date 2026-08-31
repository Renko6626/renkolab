# card — 卡牌 / 能力系统（TH18 特有）
> **版本**：跨版本。本文出现的地址一律带版本前缀（如 `th16:0x442560`）。


TH18《虹龍洞》用**卡牌/能力系统**取代了 TH16 的季节系统。它不是一个小功能，而是一整条
横跨 玩法 / 商店 / HUD / 存档 / replay 的纵向系统——这也是为什么「加一张新卡」不能只往
静态注册表后面追加一项。

放在 `engine/card/` 而不是 `th18/` 目录下，是刻意的：**特有机制也是子系统**。
将来 TH19 若有类似机制，矩阵加一列即可，不必再开版本目录。

## 断言 × 版本矩阵

| 断言 | th16 | th18 | 证据 |
| --- | :---: | :---: | --- |
| 存在卡牌/能力系统 | ❌ | ✅ | [th18/cards-01 §0](th18/cards-01-system-architecture.md) |
| `AbilityManager` 统一负责分配 / 选中 / 每帧 tick | ❌ | ✅ | [th18/cards-01 §1](th18/cards-01-system-architecture.md) |
| 主动卡按 C 键触发，带充能 | ❌ | ✅ | [th18/cards-01 §2](th18/cards-01-system-architecture.md) |
| 卡牌分类写在 `card->flags(+0x50)` 的位义里 | ❌ | ✅ | [th18/cards-01 §3](th18/cards-01-system-architecture.md) |
| 装备/射击卡带**每卡一份 .sht**，经 `Player__allocate_option` 挂子机 | ❌ | ✅ | [th18/cards-01 §4](th18/cards-01-system-architecture.md)、[th18/cards-05 D](th18/cards-05-card-catalog.md) |
| ↑ 但这些 shooter 数据**存在哪里**仍未定 | — | 🟡 | [th18/cards-OPEN](th18/cards-OPEN-passive-shooter-data.md) |
| X 键炸弹系统与卡牌**并行存在**（不是被取代） | ✅ | ✅ | th16：[player/OVERVIEW](../player/OVERVIEW.md)；th18：[cards-01 §4B](th18/cards-01-system-architecture.md)、[cards-02 §1](th18/cards-02-bomb-life-resource-economy.md) |
| 58 项**静态**注册表 `zTableCardData[]` | ❌ | ✅ | [th18/cards-03](th18/cards-03-card-registry-dump.md)、[th18/cards-05](th18/cards-05-card-catalog.md) |
| 商店 offer = 随机 + 保证 混合（`AbilityShop__initialize` `th18:0x4171B0`），卡也可由道具直接掉落 | ❌ | ✅ | [th18/cards-04 §2,§2b](th18/cards-04-card-shop.md) |
| 关卡可用性由 `CardData__is_available_at_stage` `th18:0x416E10` 判定（**订正**了原 `_for_difficulty` 命名） | ❌ | ✅ | [th18/cards-04 §3](th18/cards-04-card-shop.md) |
| 存档与 replay 保存 card-id 字节数组 | ❌ | ✅ | [th18/cards-04 §5](th18/cards-04-card-shop.md) |

> **图例**：✅ 该版本一手验过（证据列给地址/出处） · 🟡 待验（从别的版本借来的假设，或单源） · ❌ 已知不同/不存在 · ❓ 存疑 · — 未看
>
> **本页不许出现没有出处的断言。** 从某作借到另一作的判断一律 🟡，在该版本 exe 上验过才能改 ✅（[`METHOD.md`](../../METHOD.md)）。

## ★ 加新卡的关键判断

**新增卡不能只往 `zTableCardData[]` 后面写一项。** 零售表是静态的，而
`allocate_new_card` 的 ID→类分派、商店的表遍历、UI、解锁位、存档/replay
**各自都可能假设了零售卡集合**。要做完整的新卡，这些必须以同一套新 ID/元数据模型
一起设计和验证——路线见 [`../../mods/th18.v1.00a/card-rework/ROADMAP.md`](../../mods/th18.v1.00a/card-rework/ROADMAP.md)。

## 社区交叉验证

[th18/cards-06](th18/cards-06-community-crosscheck.md) 记录了与 THBWiki 的逐项对账：
高度一致，社区解开了我们几处 🟡；**分歧处社区全对，代码侧已订正**。
⚠️ [`cards-DEEPRESEARCH-salvage.md`](th18/cards-DEEPRESEARCH-salvage.md) 是**未合并的原始素材**，
不要从中直接抄实现结论。

逐卡特征化的待办清单在 [`cards-TODO-58card-characterization.md`](th18/cards-TODO-58card-characterization.md)。
