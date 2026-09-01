# TH18 卡牌系统 — 对象模型与数据布局

> **版本**：TH18 v1.00a（`th18.exe`）。本文裸地址默认属该版本；引用其他版本须写成 `th16:0x…`。
> **方法**：一手反编译/反汇编（ghidra-re MCP，db `th18`）+ ExpHP `th-re-data` 的结构体与命名。
> **可信度**：布局与偏移 ✅；标 🟡 处已逐条注明。

## 0. 一句话结论

卡牌系统是**一个全局管理器 + 一条双向链表 + 一张静态注册表 + 一个 21 槽虚表**。
`AbilityManager` 持有链表并每帧驱动；每张卡是 `zCardBaseClass`（0x54 字节）的子类，
只覆盖自己关心的虚表槽；卡的静态数据（名字、价格档、出现规则、图标）在
`zTableCardData[]` 里，运行时对象只存一个指针指过去。

四张相关的图：**对象**（本文）→ **生命周期**（[`02-lifecycle.md`](02-lifecycle.md)）→
**钩子**（[`03-hooks.md`](03-hooks.md)）→ **C 键释放**（[`04-active-cards.md`](04-active-cards.md)）。

## 1. `zCardBaseClass`（0x54 字节，ExpHP 结构体 + 一手核对）

| 偏移 | 名 | 类型 | 一手核对 |
| --- | --- | --- | --- |
| +0x00 | `vtable` | `zVTableCard*` | ✅ 由 `allocate_new_card` 按 card_id 写入 |
| +0x04 | `card_id` | int | ✅ 分配尾部写入 |
| +0x08 | `array_index` | int | ✅ = 写入时的 `num_total + 1` |
| +0x0c | `list_node` | `zCardList`（16B）| ✅ `entry/next/prev/__seldom` |
| +0x1c | `anm_id_for_ingame_effect` | `zAnmId` | ✅ 主动卡把效果 VM 存这里 |
| +0x20 | ExpHP `recharge_timer` | `zTimer`（20B）| ⚠️ **实为「激活经过帧」计时器**，见 §3 |
| +0x34 | ExpHP `__timer_2__prolly_bomb_time` | `zTimer`（20B）| ⚠️ **实为「充能倒计时」**，见 §3 |
| +0x48 | `recharge_time` | int | ✅ 充能总帧数（子类构造时写死）|
| +0x4c | `table_entry` | `zTableCardData*` | ✅ 分配尾部 `TableCardData__get(card_id)` |
| +0x50 | `flags` | int | ✅ 位义见 §4 |

**0x54 之后是子类自有字段**。分配时按卡取不同大小（`operator new` 的实参，一手抓自
`AbilityManager__allocate_new_card` `0x411460` 的 57 路 case）：

| 大小 | 卡 |
| --- | --- |
| 0x54 | 纯被动 / 资源卡（无额外状态）|
| 0x58 | 装备卡（+0x54 存 option 指针）、部分被动 |
| 0x5c–0x74 | 主动卡（+0x54 状态机、+0x58 起坐标/计数）|
| 0xb4 | `CardKeiki`（id 30，4 个 option 槽各一份计时器）|
| 0xc4 | `CardClownpiece`（id 44，虚月）|

> 逐卡大小与 vtable 地址由脚本从跳转表 `0x412dac`（57 项，id 0–56）回读，**id 57 不可构造**。
> **56 个卡类的确切大小已落成数据**：`tooling/ghidra/bindings/th18.v1.00a.json` 的
> `subclass_structs.sizes`（类名由该 case 写入的 vtable 的 `+0x50` 槽反查 `Card<X>__operator_delete`）。
> 其中 31 个大于基类的，`bind_types.py` 会建同名带填充结构体（`zCardTenshi` 等），
> 免得绑定后子类字段被渲染成 `self[1].card_id` 那种误导。

## 2. `zVTableCard`（21 槽 / 0x54 字节）

槽名来自 ExpHP，**引擎调用点是一手定位的**——完整对照表在 [`03-hooks.md`](03-hooks.md)。
基类默认实现集中在 `0x413010`–`0x413173`，多数是 `ret`；有实体的三个：

- `method_38`（+0x38）`0x4130F0` = **`set_recharge_timer(n)`**：写 +0x34 计时器（current=n、previous=n−1、current_f=n）。
- `method_3C`（+0x3c）`0x413130` = **`get_recharge_remaining()`**：返回 +0x38（倒计时 current）。ExpHP 名 `get_bomb_timer` 是误名。
- `method_40`（+0x40）`0x413140` = **`is_firing()`**：返回 `flags >> 5 & 1`（即 `flags & 0x20`）。

## 3. ★ 两个计时器：ExpHP 的名字反了（订正）

`zTimer` 是 20 字节：`previous / current / current_f / __game_speed__disused / control`。
卡里有两个，ExpHP 分别叫 `recharge_timer`(+0x20) 和 `__timer_2__prolly_bomb_time`(+0x34)。
**一手证据表明这两个名字的语义是互换的**：

| 计时器 | 谁动它 | 何时 | 结论 |
| --- | --- | --- | --- |
| **+0x20** | `Timer__increment` `0x405990` | `__on_tick_2` 末尾**每帧**（游戏进行中）| **激活经过帧**：每次状态切换都清零，用于「效果放了多少帧」|
| **+0x34** | `Timer__decrement` `0x409750` | 仅 `card+0x54 == 0`（空闲）且 `+0x38 > 0` 时 | **充能倒计时**：`c_press` 的门控读 `+0x38 < 1` |

- **发现**：`CardTenshi__c_press` `0x40EBF0` 的门控是 `card+0x54 == 0 && card+0x38 < 1`，
  并在触发时把 `recharge_time(+0x48) * ABILITY_MANAGER+0xc58` 写进 +0x34 那组，同时把 +0x20 那组清零。
- **推测**：要么 ExpHP 名字对、我们读反了；要么名字互换了。
- **验证**：`CardTenshi____on_tick_2` `0x40E8C0` 里 state0 分支只对 `card+0x34` 调 `Timer__decrement`，
  函数末尾无条件对 `card+0x20` 调 `Timer__increment` `0x405990`（该函数体是 `current += 1`）。
  12 张主动卡的 `c_press` 与 `method_4C` 共用同一模板（同样的 +0x20 清零 / +0x34 装填），非孤例。
- **结论**：**+0x34 = 充能倒计时，+0x20 = 激活经过帧** ✅（TH18 v1.00a）。
- **证据**：`0x40EBF0`、`0x40E8C0`、`0x405990`、`0x409750`、`0x4130F0`、`0x413130`。

> 本仓的 Ghidra 库已在 `0x40EBF0` 落了这条订正的注释；`Timer__increment` 是我们这层给
> `FUN_00405990` 的命名。

## 4. `flags`（+0x50）位义 —— 全部一手

初始值由 `allocate_new_card` 的每个 case 写死，随后尾部把 bit0 覆盖成 `mode & 1`（[`02-lifecycle.md`](02-lifecycle.md) §2）。

| 位 | 含义 | 证据 |
| --- | --- | --- |
| `0x01` | **属于持久卡组**（存档/replay 装载）。0 = 本局临时获得 | 分配尾部 `0x412CFE`；回收 `0x4080E0` |
| `0x02` | **即时效果待施加**，由 ctor/dtor 施加后自清 | `CardLife__destructor` `0x409B80` 等 |
| `0x04` | 所有卡都置位（基础位，非分类）| 57 个 case 全部 `OR 0x4` 或经共用尾部 |
| `0x08` | **主动卡**：可被选中、可 C 键释放 | `set_selected_active_card` `0x408B00` |
| `0x20` | **正在释放中**：`c_press` 置位，`__on_tick_2` 收尾清位 | `0x40EBF0` / `0x40E8C0`；`method_40` 读它 |
| `0x40` | **装备卡**：生成子机 | HUD 分类 `0x408DE0`；计数 `0x412D6C` |

**逐卡初始 flags（从 57 路 case 回读，扣掉随后被 mode 覆盖的 bit0）**：

| flags | card_id | 类别 |
| --- | --- | --- |
| `0x02` | 1–7、36、37 | 即时/资源卡（在 ctor 或 dtor 里施加效果）|
| `0x44` | 8–20、51 | 装备卡（子机射击）|
| `0x08` | 41–50、52、53 | 主动卡（C 键）|
| `0x06` | 32 | POWERMAX：既即时（获得 +1.00 火力）又常驻（死亡保 power）|
| `0x04` | 其余（0、21–31、33–35、38–40、54–56）| 永续被动 |

> 引擎只有这三分类（主动 / 装备 / 其余）；社区的「四类」把「其余」拆成
> 「能力（永续）」和「即时」——引擎里的判据是 **bit1 是否被 ctor/dtor 消费掉**，
> 不是独立 flag 位。对账见 [`09-community-crosscheck.md`](09-community-crosscheck.md)。

## 5. `zAbilityManager` 关键偏移（一手核对）

全局 `ABILITY_MANAGER_PTR` `0x4cf298`。

| 偏移 | 语义 | 证据 |
| --- | --- | --- |
| +0x18 | `card_list_head`（`zCardList`，哨兵指回自身）| `reset_cards` `0x407DA0` |
| +0x1c | 链表首节点（遍历起点）| 各 tick 循环 |
| +0x28 | `num_total`（上限 0x100，超了分配直接返回 −1）| `0x411469` |
| +0x2c / +0x30 / +0x34 | `num_active` / `num_equipment` / `num_passive` | `0x412D67` 起三路计数 |
| +0x38 | `selected_active_card`（C 键作用对象）| `0x45C048` 的 `vtable+0x08` 调用 |
| +0x3c | 选中卡 HUD 的 anm id | `AbilityManager__on_tick` `0x408640` |
| +0x40 | HUD 让位标志（玩家进左下角时把选中卡图标移开）| `0x408640` |
| +0x44 | HUD 计时器（每帧 `Timer__increment`）| `0x408640` |
| +0x58 | `int[256]`：所有 HUD 卡图标的 anm id | `create_all_card_lists_for_hud` `0x408D00` |
| +0x458 | `int[256]`：**主动卡**图标 anm id | `create_card_list_for_hud` `0x408DE0` |
| +0x858 | `int[256]`：**主动卡**对象指针（与 +0x458 同序）| 同上 |
| +0xc58 | **充能倍率**（float，reset 置 `1.0`；`CardByakuren` 置 `0.8`）| `0x407DA0` / `0x40CBD0` |
| +0xc5c | 卡组存档槽索引 | `0x407DA0` |
| +0xc84 | `int[56]`：**每卡「本局已拥有过」标志**（商店去重用）| `0x412D42`、`0x4171B0` |

## 6. `zTableCardData[]` 静态注册表

数组 `0x4c53c0`，stride **0x34**，止于 `0x4c5f8c` → **58 项**（id 0–57）。
`TableCardData__get` `0x407D70` 线性查 `+0x04 == card_id`，未命中返回 BLANK 项 `0x4c5f20`。

| 偏移 | 语义 | 来源 |
| --- | --- | --- |
| +0x00 | `internal_name`（`char*`，内部代号，非显示名）| ExpHP |
| +0x04 | `card_id` | ExpHP |
| +0x10 | **价格档位**（索引价格表 `0x4b35c4`）| 一手 ✅ `0x416DD0` |
| +0x14 | **抽卡权重 / 类别**（商店随机要求 `!=0 && !=6`；`==0` 是必出的资源卡）| 一手 ✅ `0x416F50`、`0x4171B0` |
| +0x18 | **出现规则 `dmode`**（0–12，见 [`05-shop-and-money.md`](05-shop-and-money.md) §3）| 一手 ✅ `0x416E10` |
| +0x1c | **可重复购买**（≠0 时即便已拥有仍会进商店池）| 一手 ✅ `0x416F50`、`0x4171B0` |
| +0x28 | **在被动卡 HUD 行显示**（==0 则不画）| 一手 ✅ `0x408DE0` |
| +0x2c / +0x30 | `sprite_large` / `sprite_small` | ExpHP |
| +0x08、+0x0c、+0x20、+0x24 | 仍未知 | — |

逐项数值见 [`07-registry.md`](07-registry.md)。

## 7. 相关全局（本仓命名，已回落 Ghidra 库）

`GlobalsInner` 块基址 `0x4cccdc`（`CURRENT_STAGE` 就是它的 field0）。

| 全局 | 地址 | = 基址+ | 语义 |
| --- | --- | --- | --- |
| `CURRENT_STAGE` | `0x4cccdc` | +0x00 | 当前关卡（`end_stage` 自增）|
| `MONEY` | `0x4ccd34` | +0x58 | 金钱（购卡货币）|
| `MONEY_TOTAL_COLLECTED` | `0x4ccd30` | +0x54 | 本局累计收集金钱（死亡惩罚不扣它）|
| `CURRENT_POWER` | `0x4ccd38` | +0x5c | 火力（`/ +0x64` = 档）|
| `MAX_POWER` | `0x4ccd3c` | +0x60 | 火力上限 |
| `POWER_PER_LEVEL` | `0x4ccd40` | +0x64 | 一档火力（=100）|
| `INPUT_HELD` | `0x4ca428` | — | 本帧按住位 |
| `INPUT_PRESSED` | `0x4ca434` | — | 本帧**上升沿**（C 键释放读它）|

资源库存三元组（`CURRENT_BOMBS` / `BOMB_FRAGMENTS` / `MAX_BOMBS` / `LIVES_STOCK`）见
[`06-resource-economy.md`](06-resource-economy.md)。
