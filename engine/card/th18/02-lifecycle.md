# TH18 卡牌系统 — 生命周期：从分配到回收

> **版本**：TH18 v1.00a（`th18.exe`）。本文裸地址默认属该版本；引用其他版本须写成 `th16:0x…`。
> **方法**：一手反编译 + 对 `AbilityManager__allocate_new_card` `0x411460` 的反汇编尾部逐指令读。
> **可信度**：机制 ✅；「bit0 的玩法含义」标 🟡（机制本身 ✅）。
> **前置**：[`01-object-model.md`](01-object-model.md)。

## 0. 一句话结论

一张卡的一生只有一个入口 `AbilityManager__allocate_new_card(mgr, card_id, mode)`。
`mode` 决定两件事：**要不要调 ctor / dtor**（这是「即时卡」得以生效即消失的机制），
以及 **flags bit0**（这张卡属于持久卡组还是本局临时获得）。回收只有两条路：
局末的 `recount_and_recategorize_cards` 按 bit0 清扫，和 `reset_cards` 全清。

## 1. 四种 `mode`

| mode | 调用点 | 场景 |
| --- | --- | --- |
| **0** | `ItemManager__on_tick__body` `0x445A80`（道具 type `0x10`–`0x13`）| 关卡中吃到卡道具 |
| **1** | `AbilityManager__reset_cards` `0x407DA0` | 从**存档卡组**重建（开局装备）|
| **2** | `AbilityShop__on_tick` `0x417CC0`（`0x41842A` / `0x4185C7`）| **商店购买**（含空白卡免费发放）|
| **3** | `AbilityShop__sub_417880` `0x417880` | **replay 回放**复原卡组 |

其余调用点：`GameThread__thread_start` `0x442A52`、`ReplayManager__sub_462d20` `0x462E25`。

## 2. ★ 分配的共同尾部（`0x412CE4`–`0x412D9D`，逐指令）

```c
if (mgr->num_total >= 0x100) return -1;      // 0x411469  卡组硬上限 256
if (card_id > 0x38)          return -1;      // 0x411479  跳转表只有 id 0..56
// ... 57 路 case:operator new(逐卡大小) + 写 vtable + 写初始 flags ...

card->card_id     = card_id;                 // 0x412CEC
card->array_index = mgr->num_total + 1;      // 0x412CF6
card->flags       = (card->flags & ~1) | (mode & 1);   // 0x412CFE ★

if ((mode & 1) == 0)                         // mode 0 / 2
    if (card->vtable->constructor())         // +0x00
        { card->vtable->operator_delete(1); return mgr->num_total; }   // ★ 卡当场消失
if (mode & 2)                                // mode 2 / 3
    if (card->vtable->destructor())          // +0x04
        { card->vtable->operator_delete(1); return mgr->num_total; }   // ★ 同上

mgr->owned[card_id] = 1;                     // 0x412D42   +0xc84 + id*4
list_insert(&mgr->card_list_head, &card->list_node);
if      (flags & 0x08) { mgr->selected_active_card = card; mgr->num_active++; }
else if (flags & 0x40)   mgr->num_equipment++;
else                     mgr->num_passive++;
card->table_entry = TableCardData__get(card->card_id);
if (mode != 1) AbilityManager__create_all_card_lists_for_hud(mgr, 0);  // 存档批量装载不重建 HUD
mgr->num_total++;
return mgr->num_total;
```

三条值得单独记住的：

- **`mode & 1` 直接变成 flags bit0**。mode 1（存档）和 3（replay）→ bit0=1；
  mode 0（道具）和 2（购买）→ bit0=0。
- **ctor/dtor 返回非 0 就当场删卡**。这不是错误路径，而是**即时卡的实现方式**（§3）。
- **`mode & 2` 决定是否调 dtor**：所以商店购买（mode 2）会**先 ctor 再 dtor**，
  道具掉落（mode 0）只调 ctor，存档装载（mode 1）两个都不调。

## 3. ★「即时卡」为什么拿不到手就生效了

- **① 发现**：`CardLife__destructor` `0x409B80` 的全部内容是
  「若 `GAME_THREAD_PTR != 0` 且 `flags & 2`：`LIVES_STOCK += 1`（封顶 7）、通知 HUD、清掉 `flags & 2`」，
  然后 **`return 1`**。`CardLifeFragment__constructor` `0x409CC0`、`CardNazrin__constructor` `0x40A020`
  （`MONEY += 50`、`MONEY_TOTAL_COLLECTED += 50`）同构，也都 `return 1`。
- **② 推测**：返回 1 是「我已经把效果施加完了」的信号。
- **③ 验证**：分配尾部对 ctor/dtor 的非零返回一律 `operator_delete(1)` 并提前返回——
  卡**不会**进链表、**不会**计数、**不会**上 HUD。而这些卡的注册表项 `+0x1c != 0`
  （可重复购买），所以商店里买完还能再刷出来。表现完全对上「即时类」。
- **④ 结论**：**即时卡 = ctor 或 dtor 施加效果后返回 1，由分配尾部当场销毁** ✅（TH18 v1.00a）。
- **⑤ 证据**：`0x412D0D`（调 ctor）、`0x412D31`（调 dtor）、`0x412D17`（删卡）、
  `0x409B80`、`0x409CC0`、`0x40A020`、`0x409C20`。

**在 ctor 还是在 dtor 施加，取决于卡**（一手逐卡）：

| 卡 | 位置 | 效果 |
| --- | --- | --- |
| `CardLife`(1) / `CardBomb`(2) / `CardMokou`(7) / `CardNarumi`(36) | dtor | 残机 / 炸弹上限 / +3 命 |
| `CardLifeFragment`(3) / `CardBombFragment`(4) / `CardNazrin`(5) / `CardRingo`(6) | ctor | 碎片 / +50 金 / +0.50 火力 |

> 因为 mode 0（道具掉落）**只调 ctor**，只有「ctor 型」的即时卡能靠道具直接生效；
> 而注册表里能被道具给出的正是 id 3/4/5/6（[`05-shop-and-money.md`](05-shop-and-money.md) §6）——自洽。

## 4. 入链之后：每帧被谁驱动

链表被三个地方遍历（钩子对照见 [`03-hooks.md`](03-hooks.md)）：

| 遍历者 | 槽 | 门控 |
| --- | --- | --- |
| `Player__on_tick__body` `0x45BE90` case 1 | `on_tick`(+0x24) | 玩家存活 |
| `AbilityManager__on_tick` `0x408640` | `__on_tick_2`(+0x2c) | `GAME_THREAD+4 → +4 & 2` 且 `mgr+0xc60 != 0` |
| `AbilityManager__on_draw` `0x408AB0` | `on_draw`(+0x48) | 无 |

## 5. ★ 回收：`recount_and_recategorize_cards` `0x4080E0`

**唯一调用点**是 `GameThread__teardown_and_recount_cards` `0x4432C0`（我们这层的命名，
原 `FUN_004432c0`），且只在 `SUPERVISOR.gamemode_to_switch_to` 为 10 或 11 时调。

```c
num_active = num_equipment = num_passive = 0;
for (card in list)
    if ((card->flags & 1) == 0) { unlink(card); card->vtable->operator_delete(1); num_total--; }
    else { card->vtable->method_4C();  /* 重置卡内状态 */
           归类计数(flags & 8 ? active : flags & 0x40 ? equipment : passive); }
selected_active_card = 0;  再从链表尾往前挑第一张 flags&8 的卡设为选中 + 刷 HUD 精灵；
清空 mgr+0x58 的 256 项 anm id 数组。
```

- **结论**：**局末清扫掉 bit0==0 的卡 = 清掉本局靠道具/商店拿到的卡，保留存档装备的卡组** ✅（机制）。
- 「bit0 就是『持久卡组 vs 本局获得』」这层**玩法解读**标 🟡：机制与 mode 的对应是一手的，
  但 gamemode 10/11 具体是哪两个流程未逐一验，留 [`OPEN-questions.md`](OPEN-questions.md)。

## 6. 全清与重建：`reset_cards(mgr, reload)` `0x407DA0`

1. 遍历链表逐张 `vtable->operator_delete(1)`；链表哨兵指回自身；三计数与 `num_total` 清零。
2. `mgr+0xc58 = 1.0`（**充能倍率复位**——所以 `CardByakuren` 的 0.8 不跨局残留）；`selected = 0`。
3. 释放预载 anm（`anm_30_ability` / `anm_31_abcard`），清 `mgr+0x58` 的 256 项 anm id。
4. **`reload != 0` 时**：清空 `mgr+0xc84` 的 56 项拥有标志，然后从存档重建卡组——
   - 张数：`SCOREFILE_PTR + 0x5f678 + slot*4`
   - 第 i 张的 card_id 字节：`SCOREFILE_PTR + 0x5f608 + slot*0x10 + i`
   - 逐张 `allocate_new_card(mgr, id, 1)`。
   → **卡组持久化在存档里：每槽最多 16 个 id 字节 + 一个张数**。

`reload == 0` 的调用（只清不重建）出现在商店的空白卡分支（[`05-shop-and-money.md`](05-shop-and-money.md) §5）
和 replay 复原。

## 7. Replay：`AbilityShop__sub_417880` `0x417880`

商店进/出时调，两个方向：

- **录制**（`GAME_THREAD+0xd0 == 0`）：把当前牌组写进 replay 分段 `+0xa64`，
  选中卡 id 写 `+0x1264`，各卡的充能剩余写 `+0xe64`，并 `GlobalsInner__assign` 存一份全局快照。
- **回放**：`reset_cards(mgr, 0)` → 从 `+0xa64` 逐个 `allocate_new_card(id, 3)`（读到负数停，上限 0x100）
  → `set_selected_active_card(+0x1264)` → 逐卡 `vtable+0x38`（`set_recharge_timer`）灌回 `+0xe64` 的剩余充能
  → `GlobalsInner__assign` 还原全局 → 逐卡 `vtable+0x20`（`on_load`）。
  最后重建 option 与 HUD。

> **replay 要能复现，卡组 + 每卡充能剩余 + 选中卡都必须存**——这三样正好是主动卡状态的全部
> 可观察量，反向印证了 §3 对两个计时器的判定（[`01-object-model.md`](01-object-model.md) §3）。

## 8. 存档里的卡牌相关字段（一手）

| 地址 | 语义 |
| --- | --- |
| `SCOREFILE_PTR + 0x5f588 + card_id` | **每卡解锁位**（1 = 买到/拿到过；影响商店权重与初始装备可选）|
| `SCOREFILE_PTR + 0x5f608 + slot*0x10 + i` | 卡组第 i 张的 card_id（字节）|
| `SCOREFILE_PTR + 0x5f678 + slot*4` | 该槽的卡数 = **初始卡槽上限**（1 → 2 → 3，解锁条件见 §9）|

## 9. 初始卡槽与解锁（`GameThread__end_stage` `0x444650`，一手）

- **通关正篇（stage 6）**：若 `SCOREFILE+0x5f678 == 1` 且 `SCOREFILE+0x5f639 == 0` → 槽位 **1 → 2**。
- **带空白卡通关**：`AbilityManager__card_exists(0)` 为真 → 成就 `0x18`，且槽位 **2 → 3**。
- **按角色解锁第二种自机卡**：`mark_obtained(9 / 0xb / 0xd / 0xf, 1)` 按 `DAT_004cccf4`（角色索引）
  → 正是注册表里 `dmode == 12`（只看解锁位）的 REIMU_OP2 / MARISA_OP2 / SAKUYA_OP2 / SANAE_OP2。
- **无续关通关**：`mark_obtained(0x37=55 MAGATAMA2, 1)` 与 `mark_obtained(0 = BLANK, 1)`。
- **通关 Extra（stage 7）**：`mark_obtained(0x36=54 MUKADE, 1)`。

`CardCollection__mark_obtained_and_notify` `0x418DE0`：置解锁位 → 若注册表前 **56** 项全部置位
则发成就 `0x1d`(29) → 排入「获得新卡」弹窗队列（`DAT_004cf2a8`，条目 = `param2 << 8 | card_id`）。
