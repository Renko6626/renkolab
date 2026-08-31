# TH18 卡牌/能力系统 — 核心架构(一手反)
> **版本**：TH18 v1.00a（`th18.exe`）。本文裸地址默认属该版本；引用其他版本须写成 `th16:0x…`。
>

> 适用:TH18(東方虹龍洞)v1.00a,`th18.exe`(database_id `th18`)。证据链纪律见
> `../METHOD.md`。引用 TH16 处显式标 `(TH16)`。
> 关联:`cards-OPEN-passive-shooter-data.md`(搁置的开放问题:被动卡 shooter 数据存储)。

## 0. 总览(可信度 ✅ 一手,除标注外)

TH18 用**卡牌(Card)/能力(Ability)系统**取代 TH16 的**季节释放(按 C)**。
⚠️ **炸弹(按 X)仍在**,与 TH16 基本同形(`Bomb` 对象 + `zVTableBomb` 角色专属 begin),**不是被卡牌取代**——
ExpHP 没命名 `zBomb` 数据结构 ≠ 没有炸弹机制(此前 port-plan 的 "TH18 无炸弹" 是误判,已订正,见 §7)。
所以 TH18 有**三套并行**:炸弹(X)、卡牌主动技(C)、卡牌被动/装备。

卡牌核心是一个**多态卡牌类层级**:基类 `zCardBaseClass`(0x54 字节)+ vtable `zVTableCard`(22 槽,ExpHP 已语义命名),
58 个具体卡类各覆盖自己关心的槽。一个全局 `AbilityManager`(`ABILITY_MANAGER_PTR` @ **`0x4cf298`**,指向堆对象)持有
**卡牌双向链表**并每帧驱动它们;玩家主 tick 与开火循环在固定接缝调卡牌 vtable 钩子。

**三类卡(由 `card->flags(+0x50)` 位区分,一手见 §3)**:主动卡(C 键触发)、装备卡(生成子机射击)、被动卡。
其中 `CardLife/CardBomb/CardLifeFragment/CardBombFragment` 是喂**残机/炸弹库存**的资源卡(见 §7)。

## 1. AbilityManager:分配 / 选中 / tick 主线

### 1a. 数据结构(`zAbilityManager`,ExpHP 命名 + 一手核对)
- `+0x18` `card_list_head`(`zCardList`,16B:`entry/next/prev/__seldom`)—— 卡牌**双向链表**头(哨兵 = 自身)。
- `+0x28/2c/30/34` = `num_total / num_active / num_equipment / num_passive` 卡数。
- `+0x38` `selected_active_card` → 当前选中的主动卡(C 键作用对象)。
- `+0x3c` 选中卡 HUD 的 anm id;`+0x58` 起三个 `int[256]` 数组 = 主动卡 HUD 的 anm vm id 表。
- `+0xc58` = 充能倍率(reset 时置 `1.0`,主动卡充能时长乘它)。
- `+0xc5c` = 卡组存档槽索引;`+0xc84` 起一段每局状态。

### 1b. `AbilityManager__on_tick`(`0x408640`)
- 门控:`GAME_THREAD` 处于游戏态(`+4→+4 & 2`)且 `mgr+0xc60 != 0`。
- **每帧遍历卡链表(`mgr+0x1c`)调 `vtable+0x2c`(`__on_tick_2`)** —— 卡牌的"管理器侧"每帧钩子。
- 其后管理选中主动卡的 HUD(anm 定位/精灵),遍历 `num_active`(+0x2c)用 `+0x58/+0x458/+0x858` 三数组。
- ⚠️ 注意:**卡牌有两个每帧钩子**——`__on_tick_2`(0x2c,管理器调)与 `on_tick`(0x24,玩家主 tick case1 调,见 §2)。

### 1c. `set_selected_active_card`(`0x408B00`)
- `param=-1` → 从链表挑**下一张 `flags&8`(主动)卡**设为 `mgr+0x38`;`param>=0` → 按 `card_id` 选。
- 命中后调 `update_selected_active_card_hud`,返回 1。→ **主动卡之间的"切换选中"**(非"使用")。

### 1d. `reset_cards`(`0x407DA0`)
- 遍历链表调 `vtable+0x50`(delete)销毁所有卡;清 0 各计数/选中/anm/三数组。
- **若 reload**:从**存档**重建卡组——`SCOREFILE_PTR + 0x5f678 + slot*4` = 卡数,
  `SCOREFILE_PTR + 0x5f608 + slot*0x10 + i` = 第 i 张卡的 **card_id 字节**;逐张 `allocate_new_card(this, id, 1)`。
  → **装备的卡组持久化在存档里**(每槽最多 16 张 id 字节 + 计数)。

### 1e. `recount_and_recategorize_cards`(`0x4080E0`,原 `sub_4080e0`,本次改名)
- 重算三计数;遍历链表:`flags&1==0`(失效)→ 从链表 unlink + `vtable+0x50` 删 + `num_total--`;
  有效 → 调 `vtable+0x4c` 刷新,再按 `flags`(见 §3)归类计数;末了重选默认主动卡 + 刷 HUD 精灵。
- 调用方:`FUN_004432c0`(卡组变更后重整)。

### 1f. 卡牌注册表(`TableCardData__get` @ `0x407D70`)
- 静态数组 `zTableCardData[]` @ **`0x4c53c0`**,stride **0x34**,止于 `0x4c5f8c` → **约 58 项**(对上 58 卡类)。
- 项:`+0x00 internal_name(char*)`、`+0x04 card_id`、`+0x2c sprite_large`、`+0x30 sprite_small`;
  `+0x08..0x2b` 原 `__unknown`,现解出 **`+0x10`=价格档位、`+0x14`=权重/类别、`+0x18`=难度可用模式**
  (一手,见 `cards-04-card-shop.md` §6),其余仍未知。
- `get(id)` 线性查 id;未命中返回 BLANK 项(`0x4c5f20`)。idx0 = "BLANK"。

## 2. 主动卡:C 键触发 + 充能(可信度 ✅)

### 2a. 引擎接缝:`Player__on_tick__body`(`0x45BE90`,状态机 `switch(player+0x476ac)`)
玩家状态机(0–4,= TH16 `+0x165a8` 的对应字段)。**case 1(存活)** 内,卡牌相关分派:
- `input & 0x400` 且(无对话 + 有敌人 + `selected_active_card!=0`)→ **`selected_card->vtable+0x08`(`c_press`)** ——**使用**选中主动卡。
- `input & 0x800` → `set_selected_active_card(-1)` **切换**选中 + 放音 `0x4e`。
- 之后遍历链表调 **`vtable+0x24`(`on_tick`)** —— 卡牌的"玩家侧"每帧钩子。

> 输入位:`0x400`=用卡、`0x800`=切卡(消费侧一手;键映射待 `Supervisor::read_keyboard_input` 重解,标 🟡)。
> `input` 全局疑为 `_DAT_004ca434`(上升沿)与 `DAT_004ca428`(held);具体位义待 §4 类工作核对。

### 2b. 主动卡生命周期(样本 `CardTenshi`:`c_press`=`0x40EBF0` / `__on_tick_2`=`0x40E8C0`)
- **状态机 `card+0x54`**:0=空闲就绪 / 1=激活中 / 2=收尾。
- **`c_press` 门控**:`card+0x54==0 && card+0x38<1`(空闲 且 充能满)。触发:捕获玩家位置→生成 ANM 效果 VM
  (存 `card+0x1c`)→ `card+0x54=1`;**装充能**:`dur = recharge_time(+0x48) * mgr+0xc58`,写入 **`card+0x34` 倒计时**。
- **`__on_tick_2`**:state0 时若有敌人且 `card+0x38>0` → `Timer__decrement(card+0x34)`(**空闲帧扣充能**);
  state1 时推进效果(本例:跟随玩家的判定圈,`BulletManager__cancel_radius_as_bomb` + `LaserManager__cancel_in_radius`
  擦弹清弹,集满阈值转 state2)。
- ⚠️ **字段订正(一手 vs ExpHP)**:ExpHP 把 `+0x20` 叫 `recharge_timer`、`+0x34` 叫 `bomb_time`,但一手看**功能相反**:
  **`+0x34` 才是门控 c_press 复用的充能倒计时**,`+0x20` 计激活时长。落 db 注释 @ `0x40EBF0`。标 🟡(单卡样本,待多卡复核)。

### 2c. 决死窗口(救命卡 **与** X 炸弹并存)
- `Player__on_tick__body` **case 4(决死窗口)** 有**两条救命路**:
  1. **救命卡**:遍历链表调 **`vtable+0x0c`(`on_player_death_after_deathbomb`)**,**OR 累加返回值;非零 → `cancel_impending_death`
     取消死亡**。`param`=累加器,保证只一张卡生效。样本 `CardEirin`(`0x40A4F0`)满足条件返回 1(复活)。
  2. **X 决死炸**:`input&0x2` 且 `Bomb__can_bomb_and_deathbomb_check()` → `do_bomb()` + `cancel_impending_death`(见 §4B)。
- case 2(死亡结算 frame3)另调 **`vtable+0x14`(`on_player_death_after_deathbomb_frame_2`)**。

## 3. 卡牌分类:`card->flags(+0x50)` 位义(一手,见 §1e)
- `0x01` = 卡有效/存活(清则被回收)。
- `0x08` = **使用类/主动卡**(可被 `set_selected_active_card` 选中、C 键 `c_press`)。
- `0x40` = **装备类卡**(生成子机射击,见 §4)。
- 三位皆非 = **被动**(计入 `mgr+0x34`)。
- 分别计入 `mgr+0x2c(active)/+0x30(equipment)/+0x34(passive)`。
- ⚠️ **订正(wiki 交叉验证)**:wiki 分**4 类**——使用/装备/**能力类**(永续被动)/**即时类**(获得即生效)。
  引擎 `flags` 的三分类把后两者都归"被动";**即时类 = 资源卡**(`CardLife/CardBomb/...`,在构造/析构经 `flags&2`
  施加效果后即消耗,见 `cards-02`),**能力类 = 永续被动**(`on_bullet_created`/`on_tick_shooters` 等钩子)。
  即:`flags` 位只分 3 档,第 4 类靠"是否在构造即施加并消耗"区分,非独立 flag 位。

## 4. 装备/射击卡:子机 + 每卡 .sht(可信度 ✅;数据存储 🟡 见 OPEN 文档)

**模型(样本 `CardReimu1/2`、`CardMarisa1`、`CardSakuya1`)**:
1. `on_power_level_change`(vtable **0x18**)→ `Player__allocate_option(this, this, posX, this, posY, 2)` 生成**子机/option**,
   存 **`card+0x54`**(位置偏移逐卡不同:Reimu1=+0x30、Reimu2=−0x18)。
2. `on_tick_shooters`/`on_shoot`(vtable **0x1c**)→ 由 **`Player__tick_shooting_state`(`0x45EA00`)** 每射击帧遍历链表对**每张卡**
   调用,传 `(short_timer=player+0x476d4, long_timer=player+0x476e8)`;装备卡转发
   `Player__tick_shooters_for_ability_card(子机, short, long, 该卡索引)`(`0x40A9C0`)。
3. 子弹从**子机位置**(option+0x5c/0x60)按**逐卡烘死的 shooter 索引**取一张 SHT shooter 表(stride 0x5c、符号位终止,
   `(TH16)` shooterset 同形)开火 `Player__shoot_one_bullet`(`0x45E930`)。
   **逐卡索引**:Reimu1=`0xa`、Reimu2=`0x12`、Marisa1=`0xb`、**Sakuya1=`0xc+聚焦?1:0`**(聚焦位 `player+0x476cc`,= `(TH16)+0x165c8`)。
4. **取表式**:`*(char**)(*(int*)(player+0x47940)+0xe0+idx*4)` —— player 的 SHT 数据指针 `+0x47940`,`+0xe0` 一组 shooter 表。
   → **这些表的实际存储是开放问题**(只解包 pl00–03):见 `cards-OPEN-passive-shooter-data.md`。

> `Player__tick_shooting_state` 同时也跑**玩家本体基础 shot**(同一 `+0x47940/+0xe0/idx*4` 取表),与卡牌子机是两条并行发射路径。
> 含 option 槽门控:shooter `+0x21==2`(子机弹)时须对应 option 槽激活才发(`(TH16)` 同形)。

## 4B. 炸弹(X 键)系统 — 与卡牌并行(可信度 ✅,库存全局 🟡)

TH18 **保留** TH16 式炸弹(此前误以为被卡牌取代,订正见 §7)。是个真 `Bomb` 类(`Bomb__operator_new` `0x41FD40` 按角色选
vtable:`BombReimuAInf/BombMarisaAInf/BombSakuyaInf/BombSanaeAInf`,`zVTableBomb` 28B/7 槽:`operator_delete/begin/on_tick/on_draw/...`)。
> ✅ 对抗复核(2026-06-13)字节级确证:`do_bomb` 从活的玩家 tick 可达,`CURRENT_BOMBS/MONEY/CURRENT_POWER/BOMB_FRAGMENTS` 指令级核对;"TH18 无炸弹"假设确证被推翻。

- **`do_bomb`(`0x420360`)**:`input&0x2`(X)触发。门控 `BOMB[0xc]==0`(未在炸)→ 置炸弹进行中(`BOMB+0xc=1`)、
  重置计时(`BOMB+0xd/0x10/0x11`)、spell 中炸置失败标记(`BOMB+0x1a`)、放音 `0x2c`、
  **调 `BOMB->vtable+0x4`(`zVTableBomb.begin`,角色专属炸弹)**、清 `ENEMY_MANAGER+0x44`。→ 与 `(TH16)` 主炸同形。
- **`Bomb__can_bomb_and_deathbomb_check`(`0x420420`,本次改名)**:`CURRENT_BOMBS > 0` + `BOMB+0x30!=1`
  + 无对话 + 有敌人 → 可炸。普通炸(case1)与决死炸(case4)都走它。
- **资源卡喂库存**(详见 `cards-02-bomb-life-resource-economy.md`):炸弹三元组 `CURRENT_BOMBS`(`0x4ccd58`)/
  `BOMB_FRAGMENTS`(`0x4ccd5c`)/`MAX_BOMBS`(`0x4ccd64`);`CardBomb` 抬上限、`CardPatchouli` 给当前炸、
  `CardLife/CardLifeFragment/CardMokou` 喂残机(`LIVES_STOCK` `0x4ccd54`)。`Card__death_save_bomb_revive`
  (`0x40A2A0`)= CardEirin 决死救命,消耗 `CURRENT_BOMBS`。→ 此前 "0xd58 vs 0xd64" 🟡 **已对清**。

## 5. vtable 接缝速查(`zVTableCard`,一手确认的引擎调用点)

| 槽 | 名 | 引擎调用点(地址)| 语义 |
| --- | --- | --- | --- |
| 0x08 | `c_press` | `Player__on_tick__body` case1,`input&0x400`(`0x45C0xx`)| 使用选中主动卡 |
| 0x0c | `on_player_death_after_deathbomb` | 同上 case4 | 救命卡;OR 非零→取消死亡 |
| 0x14 | `..._frame_2` | 同上 case2(frame3)| 死亡结算钩子 |
| 0x18 | `on_power_level_change` | `Player__repopulate_options_and_notify_cards`(`0x45D5E0`)尾部 | power 变时广播;装备卡生成子机 |
| 0x1c | `on_tick_shooters`/`on_shoot` | `Player__tick_shooting_state`(`0x45EA00`)| 每射击帧;装备卡子机开火 |
| 0x24 | `on_tick` | `Player__on_tick__body` case1 | 玩家侧每帧钩子 |
| 0x28 | `on_bullet_created` | `PlayerBullet__create`(`0x45E320`)尾部 | 每生成一颗自机弹,对每卡调(传新弹)|
| 0x2c | `__on_tick_2` | `AbilityManager__on_tick`(`0x408640`)| 管理器侧每帧钩子 |
| 0x50 | `operator delete` | `reset_cards` / `recount` | 销毁 |

## 6. 开放/待办(主线已覆盖,以下为缺口)
- ✅ **`on_power_level_change`(0x18)调用点** = `Player__repopulate_options_and_notify_cards`(`0x45D5E0`)尾部(2026-06-13 定位)。
- ✅ **`on_bullet_created`(0x28)调用点** = `PlayerBullet__create`(`0x45E320`)尾部(2026-06-13 定位);用途:卡按需改/响应每颗自机弹。
- 🟡 **被动卡 shooter 数据存储** → `cards-OPEN-passive-shooter-data.md`(计划单开 deep research)。
- ⏳ **58 卡逐张刻画**(效果、id、`__unknown` 数值表)—— 适合后续 workflow 扇出,registry @ `0x4c53c0`。
- ⏳ 输入位映射(0x2 炸 / 0x400 用卡 / 0x800 切卡)到 `Supervisor::read_keyboard_input` 重解。
- ⏳ `recharge` 字段订正(§2b)需多张主动卡复核才升 ✅。
- 🟡 **炸弹库存全局对账**(§4B):`DAT_004ccd58` vs `DAT_004ccd64` 的分工 + `CardBomb`/`CardLife` 资源经济。

## 7. 订正记录(发现→纠错)
- **2026-06-13:港计划"TH18 无炸弹"误判 → 订正**。`00-port-plan.md` / README 据 "ExpHP `zBomb` MISSING" 推断 TH18 无炸弹,
  把炸弹也算进卡牌取代范围。**一手证伪**:存在 `BOMB_PTR`、`do_bomb`(`0x420360`,X 键)、`Bomb__operator_new`(`0x41FD40`)、
  `zVTableBomb`(角色专属 begin)。→ **TH18 保留 TH16 式炸弹(X);卡牌只取代季节释放(C)**。ExpHP 未命名 `zBomb` 数据
  结构 ≠ 无炸弹机制。证据:§4B。教训:别把 "ExpHP 没命名某结构" 当 "该机制不存在"。
- **2026-06-13:`on_shoot` 卡 ≠ 改基础 shot → 订正**。初判 "主 shot 就是装备卡",一手证伪:装备卡是 `Player__allocate_option`
  生成的**自主子机**,按逐卡 .sht 索引开火,与本体基础 shot 并行(§4)。
