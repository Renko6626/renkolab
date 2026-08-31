# TH18 炸弹/残机 资源经济 — 卡牌喂库存(一手反)

> 适用:TH18 v1.00a,`th18.exe`(`th18`)。前置:`cards-01-system-architecture.md`(架构)。
> 证据链纪律见 `../METHOD.md`。

## 0. 一句话
TH18 的**炸弹(X)/残机库存不是普通计数器,而是由资源卡喂养**:`CardBomb/CardLife/...` 在
构造/析构时改全局库存。炸弹本体(X 键 `do_bomb`)消费库存,与卡牌系统正交。

## 1. 炸弹库存三元组(可信度 ✅)

HUD 更新函数 `Gui__sub_4420e0(GUI, CURRENT_BOMBS, BOMB_FRAGMENTS, MAX_BOMBS)` 三参,坐实三元组:

| 全局(本次命名)| 地址 | 语义 | 证据 |
| --- | --- | --- | --- |
| `CURRENT_BOMBS` | `0x4ccd58` | 当前可用炸弹 | `Bomb__can_bomb_and_deathbomb_check`(`0x420420`)门控 `>0`;`Card__death_save_bomb_revive` 消耗;钳到 `MAX_BOMBS` |
| `BOMB_FRAGMENTS` | `0x4ccd5c` | 炸弹碎片(集齐进位)| `ItemManager__on_tick__body` 收集时写;`CardPatchouli` 满时清 0 |
| `MAX_BOMBS` | `0x4ccd64` | 炸弹上限 | `CardBomb__destructor` `+1`(cap 7);`CURRENT_BOMBS` 处处钳到它 |

- **消费**:`do_bomb`(`0x420360`,X)经 `BOMB->vtable+0x4`(角色 begin)放炸;`Card__death_save_bomb_revive`
  (`0x40A2A0`,原 `FUN_0040a2a0`,CardEirin 决死调)消耗 `CURRENT_BOMBS`(**递减约 2**,钳到 `MAX_BOMBS`)+ 清屏 + 复活。
- **补货**:`CardPatchouli____on_load__2`(`0x409F40`)装备时 `CURRENT_BOMBS +1`(音效 0x2e);`CardBomb` 抬 `MAX_BOMBS`。

## 2. 残机库存(可信度 🟡 — 需与 CURRENT_LIVES 对账)

| 全局 | 地址 | 写入方 | 备注 |
| --- | --- | --- | --- |
| `LIVES_STOCK_cardfed_cap7` | `0x4ccd54` | `CardLife__destructor`、`CardLifeFragment__constructor`、`CardMokou__destructor`(均 `+1` cap 7)| 残机库存(疑似上限/库存)|

- 🟡 **未定**:`LIVES_STOCK_cardfed_cap7` 与已命名 `CURRENT_LIVES`(Player on_tick case2 `<0`→GameOver)的确切关系(当前 vs 上限 vs 碎片)。
  `CardLife`(整命)与 `CardLifeFragment`(碎片)都 `+1` 到同一全局,语义待进一步反(可能是"库存上限",碎片进位逻辑在别处)。
- 残机似乎**无炸弹那样的清晰三元组**(未见 life 版 `Gui__sub_4420e0`);留作 follow-up。

## 3. 资源卡 → 库存映射(一手)

| 卡 | 触发点 | 效果 | 门控 |
| --- | --- | --- | --- |
| `CardBomb` | `__destructor`(`0x409C20`)| `MAX_BOMBS += 1`(cap 7)| `card flags(+0x50) & 2` |
| `CardBombFragment` | `__constructor`(`0x409D60`)| `FUN_004576e0`(碎片进位处理)| 同上 |
| `CardLife` | `__destructor`(`0x409B80`)| `LIVES_STOCK +1`(cap 7)| 同上 |
| `CardLifeFragment` | `__constructor`(`0x409CC0`)| `LIVES_STOCK +1`(cap 7)| 同上 |
| `CardMokou` | `__destructor`(`0x409DF0`)| 写 `LIVES_STOCK` | 待细反 |
| `CardPatchouli` | `__on_load__2`(`0x409F40`)| `CURRENT_BOMBS += 1` | 无(装备即给)|

- **`flags(+0x50) & 2` = "本帧应施加效果"门控**:置位时施加库存改动后清掉(`&= ~2`)。构造时施加(碎片/Patchouli)
  vs 析构时施加(整命/整炸)的区别 = 卡"获得时给"还是"消耗时给",🟡 待逐卡确认。

## 4. 对账结论(订正 cards-01 §4B 的 🟡)
- ✅ `0x4ccd58` = `CURRENT_BOMBS`(门控/消费),`0x4ccd64` = `MAX_BOMBS`(`CardBomb` 抬升)—— 此前 "0xd58 vs 0xd64 分工未定" **已解**:
  当前 vs 上限。中间 `0x4ccd5c` = `BOMB_FRAGMENTS`。

## 5. Follow-up(资源经济仍有缺口)
- 🟡 残机三元组/`LIVES_STOCK` vs `CURRENT_LIVES` 对账(§2)。
- ⏳ `ItemManager__on_tick__body`(`0x445A80`)完整道具→资源 dispatch(碎片/power/分数续命),含 `BOMB_FRAGMENTS` 进位阈值。
- ⏳ 资源卡构造 vs 析构施加效果的时机语义(§3 门控),逐卡确认。
- ⏳ `do_bomb` 的角色 begin(`zVTableBomb.begin`)是否在 begin 内扣 `CURRENT_BOMBS`(本文只确认 death-save 扣)。
