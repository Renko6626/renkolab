# 【待办·后续 workflow】58 张卡逐张效果刻画
> **版本**：TH18 v1.00a（`th18.exe`）。本文裸地址默认属该版本；引用其他版本须写成 `th16:0x…`。
>

> 状态:⏳ **搁置**,留给后续 **workflow 扇出**(用户已同意此类"宽"活才开 workflow)。
> 适用:TH18 v1.00a,`th18.exe`(`th18`)。架构前置见 `cards-01-system-architecture.md`。

## 目标
逐张刻画全部 ~58 张卡的**效果语义**:每卡是主动/装备/被动、覆盖了哪些 vtable 槽、做什么、关键数值。
架构(分配/选中/tick、c_press/充能、装备子机、炸弹/资源)已在 `cards-01` / `cards-02` 反清,这里只剩**逐卡填表**。

## 已就位的锚点(workflow 起手即用)
- **卡牌注册表**:静态数组 `zTableCardData[]` @ **`0x4c53c0`**,stride **0x34**,止 `0x4c5f8c`,~58 项。
  项:`+0x00 internal_name(char*)`、`+0x04 card_id`、`+0x10 价格档位`、`+0x14 权重/类别`、`+0x18 难度可用模式`
  (后三个一手已解,见 `cards-04-card-shop.md` §6)、`+0x2c/0x30 sprites`;`+0x08..0x2b` 仍有未知字节。
  → 先 dump 这张表得 (card_id, internal_name, 价格档, 难度模式) 全清单。
  价格表 `0x4b35c4`(档位→金额)、解锁位 `SCOREFILE+0x5f588+id`、特殊卡 id `0x23/0x26/0x27`(见 cards-04 §7)也已锚定。
- **每卡类**:58 个 `Card*` 类,命名见 ExpHP;各 override 的槽 = 反编译该类非空方法即知。
  vtable 语义见 `cards-01` §5(`c_press`/`on_tick_shooters`/`on_player_death_after_deathbomb`/`on_power_level_change`/…)。
- **分类位**:`card->flags(+0x50)`:0x01 有效 / 0x08 主动 / 0x40 装备 / 否则被动(`cards-01` §3)。

## workflow 设计建议(成本意识,见 memory `re-workflow-fanout-cost`)
- **形状已知 = 适合 workflow**:固定 worklist(58 卡)→ 每卡一个子 agent 反它覆盖的方法 + 查注册表数值 → 结构化输出。
- **省钱**:命名/刻画用 **sonnet**;**≤10 卡/批**(ghidra 扇出贵,20 候选≈1M token);先 inline dump 注册表得清单再扇出。
- **对抗验证**:对"超过社区"的逐卡结论按 `00-METHOD` 闸门复核(尤其 `__unknown` 数值的量纲)。
- **被动卡 shooter 数据**那条开放问题(`cards-OPEN-passive-shooter-data.md`)是独立 deep research,**不要混进**这个逐卡 workflow。

## 产出
- 每卡一行:`card_id / internal_name / 类别 / 覆盖槽 / 效果摘要 / 关键数值 / 可信度`。落 `th18/findings/cards-03-card-catalog.md`。
