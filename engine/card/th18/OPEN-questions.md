# TH18 卡牌系统 — 开放问题清单

> **版本**：TH18 v1.00a（`th18.exe`）。本文裸地址默认属该版本；引用其他版本须写成 `th16:0x…`。
> **用途**：把「已知不知道」集中登记，免得散落在各篇的 Follow-up 里被忘掉。
> 本文**不下结论**，只钉住问题、已有线索和验法。

## 1. ✅ 已解决（2026-09-05）：装备卡的子机 shooter 数据存在哪

**答案：假设 1 成立** —— 就在四个 `pl0X.sht` 里。`+0xe0` 是一张 **40 项**的 shooterset 偏移数组
（数据区起点 `+0x180` 是硬编码常量），其中：

| 索引 | 内容 |
| --- | --- |
| `0x00`–`0x09` | 自机主炮（火力档 0–4 × 非聚焦/聚焦）|
| **`0x0a`–`0x16`** | **13 组装备卡子机弹幕**，四个角色的文件同构（所以卡里能把索引烘死成立即数）|
| `0x17`–`0x27` | 空位（值 0），17 个 |

全文见 [`../../sht/th18/01-file-layout-and-shooterset-index.md`](../../sht/th18/01-file-layout-and-shooterset-index.md)
（布局 / 装载解析 / 索引分配）与 [`../../sht/th18/02-shooter-record.md`](../../sht/th18/02-shooter-record.md)
（`0x5c` 字段图 / 发射判定 / 瞄准链路）。另外两个假设**被证伪**：表不在 exe 的 `.rdata`（假设 2），
索引也不跨卡复用（假设 3，11 张卡 11 个不同索引 + Sakuya 按聚焦占两个）。

对 mod 的两条推论：**子机与其子弹的贴图都取自 `ability.anm`**；**瞄准 = 写 `player+0x479cc` +
`func_on_init = 5`**。见 [`03-hooks.md`](03-hooks.md) §5。

## 2. 🟡 `zTableCardData` 仍未知的字段

已解出 `+0x10`(价格档)、`+0x14`(权重/类别)、`+0x18`(dmode)、`+0x1c`(可重复购买)、
`+0x28`(被动 HUD 行显示)。**仍未知：`+0x08`、`+0x0c`、`+0x20`、`+0x24`。**

线索：[`07-registry.md`](07-registry.md) 的 dump 里 `f08` 只取 0/1、`f0c` 取 0–4
（看着像分页/图鉴分类）。*验法*：`search_bytes` 找读 `entry+0x08` / `+0x0c` / `+0x20` / `+0x24`
的指令（`8B 4? 08` 之类），逐个反宿主函数。

## 3. 🟡 `flags` bit0 的玩法含义

机制是一手的：分配尾部 `flags bit0 = mode & 1`，
`recount_and_recategorize_cards` `0x4080E0` 删掉 bit0==0 的卡。
**未验**：`GameThread__teardown_and_recount_cards` `0x4432C0` 里触发 recount 的
`SUPERVISOR.gamemode_to_switch_to == 10 / 11` 具体是哪两个流程。
在此之前，「bit0 = 持久卡组 vs 本局临时」只是最自洽的解读，不是闭合证明。
*验法*：反 `SUPERVISOR.gamemode_to_switch_to` 的全部赋值点，做一张 gamemode 编号表。

## 4. 🟡 两张主动卡的充能字段没在构造里赋值

`CardYukari`（41 WARP）与 `CardTsukasa`（52 CYLINDER）的 `allocate_new_card` case 里
没看到写 `card+0x48`（`recharge_time`）。前者的 `c_press` `0x40A1B0` 读 `INPUT_HELD`
决定瞬移方向，可能压根不用倒计时；后者 `0x410E60` 直接走炸弹路径。
*验法*：把这两张卡的 `c_press` 与 `__on_tick_2` 完整反一遍，确认门控读的是不是 `+0x38`。

## 5. 🟡 金钱身价的常量未 dump

[`05-shop-and-money.md`](05-shop-and-money.md) §2 的金钱→分数公式里，
`0x4ccd28`/`0x4ccd2c`（上下限）、`0x4b93ac`（Easy 系数）、`0x4b9304` 的实际数值未读。
*验法*：`read_bytes` 直接读；上下限是运行时写入的，需找写入点。

## 6. ⏳ 逐卡刻画的剩余空白

[`08-catalog.md`](08-catalog.md) 已覆盖全部 56 张可获得卡的效果方向与关键数值，
但仍有零星 🟡（`ITEM_CATCH`/`ITEM_LINE` 写进玩家字段的精确尺度、`RICEBALL` 的 power 分支）。
这些是**单卡级别**的收尾，不需要再开扇出式 workflow；按需一张一张补即可。

## 7. ⏳ 输入层的键位映射

引擎侧到「位」为止是一手的（[`04-active-cards.md`](04-active-cards.md) §1）：
`0x400` 用卡、`0x800` 切卡。**位 → 物理按键**由可配置的输入层决定，
`INPUT_HELD` 的原始来源是 `DAT_004ca210`。
*验法*：反 `DAT_004ca210` 的写入方（`FUN_00474850` / `FUN_00401c50` 有 xref），
并找按键设置界面的字符串（注意 Ghidra 认不出 Shift-JIS，见
[`../../../games/th18.v1.00a/INDEX.md`](../../../games/th18.v1.00a/INDEX.md)）。
