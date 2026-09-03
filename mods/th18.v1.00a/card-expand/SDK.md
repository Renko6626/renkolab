# SDK —— 给一张新卡写行为

> **版本**：TH18 v1.00a（`th18.exe`，imagebase `0x400000`）。本文裸地址默认属该版本；引用其他版本须写成 `th16:0x…`。
> 面向**写行为的人**：一张卡的登记在 [`DATA.md`](DATA.md)（JSON），行为在这里（C）。两层按 id 绑定，各自能独立验证。
> 本文既是使用说明也是设计文档；机制上的每一条断言都有 AUDIT §O 的条目对应。

## 0. 一张有行为的卡长什么样

```c
/* native/cards/ace_spade.c —— A♠：Miss 后无敌时间 +50% */
#include "sdk.h"

static int on_death_frame2(ce_card_t *c)
{
    (void)c;
    ce_player_invuln_scale(1.5f);
    return 0;
}

CE_CARD(62, .on_death_frame2 = on_death_frame2);
```

加上 `th18/cards.js` 里的 `"62": {…}`，这张卡就完整了。`CE_CARD` 展开成：这张卡的回调表、一份 21 槽虚表（基类拷贝，用到的槽换成桩）、
一条登记进 `ce_behaviors[]`。**不用改任何别的文件**——`native/cards/*.c` 由 Makefile 通配。

## 1. 机制：断点换虚表，跳转表不动

零售分配器 `allocate_new_card` 对 id ≥ 57 全走 case 56（`0x411489`）：游戏自己 `new(0x54)` 一个基类 `zAbility`，
虚表 `0x4b4c78`，然后进公共尾段。尾段第一条真正的写是 `0x412cec mov [esi+4], ebx`（**esi = 卡对象，ebx = id**）。

SDK 在这里挂 thcrap 断点 `ce_card_bind`（cavesize 6：这条 + 后面的 `mov eax,[edi+0x28]`，都无相对寻址）：

```
if (ebx 在 ce_behaviors[] 里)  *(void **)esi = 那张卡的虚表;
return 1;   /* 放行原指令 */
```

换完虚表之后尾段照常：`mode 0/2` 调 ctor 槽（`0x412d11`）、`mode 2/3` 调 dtor 槽、入链、`owned[id]=1`、`+0x4c` = 表行指针、
建 HUD。所以：

- **构造 / 析构语义与零售完全一致**（`02-lifecycle.md` §2）：ctor 返回非 0 = 当场删卡 = 即时卡。
- **对象由游戏分配和释放**，大小固定 0x54；SDK 不碰堆。
- **没有手写机器码**：桩是编译器生成的 `__thiscall` 函数。
- 没登记行为的新卡什么也不发生（虚表仍是基类 = 全 `ret`），和现在一样。

## 2. 对象与虚表

基类对象 0x54 字节（一手，case 56 与尾段）：

| 偏移 | 字段 |
| --- | --- |
| +0x00 | 虚表 |
| +0x04 | `card_id` |
| +0x08 | `array_index`（分配序号）|
| +0x0c..+0x1b | 链表结点（`mgr+0x18` 表头，`0x412e90` 插入）|
| +0x30、+0x44 | 位标志（case 56 清 bit0）|
| +0x48 | 充能时长（主动卡）|
| +0x4c | `zTableCardData*`（尾段写）|
| +0x50 | flags：bit0 = 存档/replay 装载，bit3 = 主动，bit6 = 装备，bit5 = 开火中 |

21 个槽（`03-hooks.md` §1 的语义；签名由基类实现的 `ret N` 定，`this` 在 ecx）：

| 槽 | SDK 回调名 | 签名 | 备注 |
| --- | --- | --- | --- |
| +0x00 | `ctor` | `int (ce_card_t*)` | 返回非 0 → 当场删卡 |
| +0x04 | `dtor` | `int (ce_card_t*)` | 同上；商店购买先 ctor 再 dtor |
| +0x08 | — | | 主动卡 C 键，第二批 |
| +0x0c | `on_death_after_deathbomb` | `int (ce_card_t*, uint32_t)` | 返回非 0 = 救下了 |
| +0x10 | `on_death_before_deathbomb` | `int (ce_card_t*)` | |
| +0x14 | `on_death_frame2` | `int (ce_card_t*)` | 死亡结算之后（扣钱扣火力已发生）|
| +0x18 | `on_power_level_change` | `int (ce_card_t*)` | |
| +0x1c | `on_tick_shooters` | `int (ce_card_t*, uint32_t, uint32_t)` | 每射击帧 |
| +0x20 | `on_load` | `int (ce_card_t*)` | 返回值 OR 累加 |
| +0x24 | `on_tick` | `int (ce_card_t*)` | 玩家侧每帧 |
| +0x28 | `on_bullet_created` | `int (ce_card_t*, void *bullet)` | 每颗自机弹 |
| +0x2c | `on_tick_2` | `int (ce_card_t*)` | 管理器侧每帧；菜单 / 商店里**不跑** |
| +0x30 | `on_enemy_drop` | `int (ce_card_t*, uint32_t, uint32_t)` | 敌人掉落道具后；两参语义 🟡 |
| +0x34 | `on_stage_start` | `void (ce_card_t*)` | 每关开场 |
| +0x38..+0x40 | — | | 充能计时器三件套，主动卡用，第一批不覆盖 |
| +0x44 | `on_hud_anm` | `int (ce_card_t*, uint32_t)` | |
| +0x48 | `on_draw` | `int (ce_card_t*)` | |
| +0x4c | `on_run_reset` | `void (ce_card_t*)` | 局末重置 |
| +0x50 | （SDK 自己占）| | 先清私有状态，再跳基类 `0x411410` |

桩按**虚表**分派，不按对象：`CE_CARD` 为这张卡生成独立的桩函数集，直接调它的回调，没有运行时查表。
没写的回调保持基类槽（`xor eax,eax; ret`）。

`ce_card_t` 就是对象指针的别名，SDK 提供取值函数：`ce_card_id(c)`、`ce_card_entry(c)`（表行）、`ce_card_flags(c)`。

## 3. 登记与对账

```c
CE_CARD(id, .回调 = 函数, ...);      /* 一张卡一条，放在 native/cards/<name>.c */
```

门里 `cards.js` 装完之后（`ce_cards_load` 之后、`ce_menu_setup` 之前）做 `ce_sdk_bind_check`：

| 情况 | 结果 |
| --- | --- |
| JSON 有、C 有 | 绑定；日志 `sdk: 62 bound (ctor, on_death_frame2)` |
| JSON 有、C 无 | 允许；日志 `sdk: 60 has no behavior (base vtable)`——开发期正常 |
| C 有、JSON 无 | **FAIL**：有行为却没登记的卡进不了游戏，是 bug |
| C 里同一 id 两次 | 编译期链接冲突（符号名含 id）|

`ce_behaviors[]` 由链接器段（`__attribute__((section("ce_cards")))`）收集，加卡不改任何清单。

## 4. 私有状态

对象没有余量。`ce_state(c, size)` 返回这张卡对象的私有内存（首次调用分配并清零，同一对象重复调用返回同一块）。
实现：DLL 侧 256 槽表，键 = 对象指针；`operator_delete` 桩释放（`reset_cards` / 局末 `recount` / 即时卡删除都走这个槽，不会漏）。
`size` 上限 256 字节；第一批只有 A♠ 需要（防止同一次死亡里放大两次）。

## 5. 引擎访问：`engine.h`

只放**一手确认过**的地址与偏移，每条带出处：

| 符号 | 值 | 出处 |
| --- | --- | --- |
| `SCORE` | `0x4cccfc` | `05-shop-and-money.md` §1 |
| `MONEY` / `MONEY_TOTAL_COLLECTED` | `0x4ccd34` / `0x4ccd30` | 同上 |
| `CURRENT_POWER` / `MAX_POWER` | `0x4ccd38` / `0x4ccd3c` | `01-object-model.md` §7 |
| `ABILITY_MANAGER_PTR` | 现有 `sites_gen.h` | 卡链表头 `+0x18`、`owned[]` `+0xd70`、充能倍率 `+0xc58` |
| `PLAYER_PTR` 与玩家字段 | ⏳ RE | 四档移速、无敌帧、道具回收四参 |
| 自机弹字段 | ⏳ RE | `on_bullet_created` 参数里的伤害（抄 `CardMomoyo`）|

辅助函数随第一批卡长出来（方案 3 的约定：先在卡里写，出现第二次就提炼进 `sdk.h`）：
`ce_player_speed_scale(f)`、`ce_player_invuln_scale(f)`、`ce_player_item_catch_set(a,b,c,d)`、`ce_bullet_damage_scale(bullet, f)`。

## 6. SDK 事件（虚表之外）

有些效果不在 21 个槽里。SDK 用 thcrap 断点补，回调写在同一张 `CE_CARD` 表里，SDK 在断点里沿 `mgr+0x18` 卡链表找出有该回调的对象逐个调：

| 事件 | 断点 | 回调 | 本批用 |
| --- | --- | --- | --- |
| `on_item_score` | `ItemManager__collect_money_item` `0x446b00`，身价算完、写 `SCORE` 前（具体指令 ⏳ RE）| `void (ce_card_t*, int *value)` | 10♠：`*value += *value / 10` |

以后加事件照此：一个断点 + 一个回调名 + AUDIT 一条。

## 7. 第一批：黑桃五张

| 牌 | id | 槽 / 事件 | 实现 | 要反的 |
| --- | --- | --- | --- | --- |
| 10♠ 道具得点 +10% | 58 | `on_item_score` | `*value += *value/10` | `0x446b00` 里写 `SCORE` 前的那条指令与寄存器 |
| J♠ 移速 +10% | 59 | `on_tick` | 每帧四档移速 = 零售值 × 1.1（零售值每关由 sht 重置，所以每帧写；读「零售值」= 先记下未放大的值）| TH18 玩家对象四档移速偏移（TH16 `+0x16650..5c`），以及谁在写 |
| Q♠ 道具回收范围 | 60 | `ctor` + `on_load` | 抄 `CardNitori`（id 21）写玩家 `+0x47988..94`，数值放大 | Nitori 构造器里四个数各自含义（🟡） |
| K♠ 伤害 ×1.1 | 61 | `on_bullet_created` | 抄 `CardMomoyo`（id 54）：`bullet->damage *= 1.1` | Momoyo 桩里弹字段的偏移与类型 |
| A♠ Miss 后无敌 +50% | 62 | `on_death_frame2` | 无敌帧计数 × 1.5 | TH18 无敌帧偏移（TH16 `+0x1663c`）；`+0x14` 触发时计数已置 |

数值（`price_tier` / `weight` / sprite）在 `patch-test/th18/cards.js` 里给；sprite 先全用 116/117 占位。
「皇家同花顺」（五张齐 → 隐藏效果）不在本批：接缝是购买 `AbilityShop__on_tick` `0x4185c7` + `owned[]`。

## 8. 开发循环

`th18/cards_dev.js`（只放 `_test`，读法同 `cards.js`）：

```json
{ "start_deck": [58, 59, 60, 61, 62], "trace": true }
```

- `start_deck`：`_test` 的初始卡组钩子改为读这个列表（现在写死 58）；空槽依次填。
- `trace`：每个桩被调记一行 `trace: card 62 on_death_frame2`（每帧槽只记第一次）。

验收 = 日志里 `sdk: … bound` 五行 + trace 行 + 游戏里体感（移速、回收、无敌时长可目测；伤害与得点看数字）。

## 9. 边界与不做的

- 主动卡（C 键、充能、HUD、replay）：第二批，SDK 加「主动卡基类」。
- 对象大小固定 0x54：要更大对象的卡走第 4 节的私有状态，不改分配。
- 事件断点每个都要过 AUDIT；本批只加一个。
- 图鉴 ≤ 127 条目（新卡 ≤ 71）、`abcard.anm` sprite 追加：另外的会话。

## 10. 文件

```
native/
├── sdk.h            写卡的人 include 这个：ce_card_t、CE_CARD、回调表、ce_state、辅助函数
├── engine.h         一手地址 / 偏移（每条带出处）
├── sdk.c            断点 ce_card_bind、对账、状态槽、事件断点、trace
├── sdk_vtable.c     基类虚表拷贝与桩的生成（CE_CARD 宏的后端）
└── cards/           每张卡一个 .c（Makefile 通配）
    ├── s10.c  sj.c  sq.c  sk.c  sa.c
```
