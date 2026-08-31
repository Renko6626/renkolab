# TH18 卡片商店 AbilityShop — 获得卡的手段(一手反)

> 适用:TH18 v1.00a,`th18.exe`(`th18`)。前置:`cards-01-system-architecture.md`(架构)、
> `cards-02-...resource-economy.md`(库存)。证据链纪律见 `../../sht/findings/00-METHOD-逆向记录纪律.md`。
> ExpHP 命名:仅 6 个 `AbilityShop::` 方法,**无 money/shop 全局、无 zAbilityShop 结构**;语义全为一手。

## 0. 一句话
每关结束的卡片商店 `AbilityShop` 是个**注册子系统**(`on_tick` 优先级 0xc / `on_draw` 0x51)。它**加权随机**
抽一批待售卡,玩家用**金钱 `MONEY`**(关卡中收集)购买,**不够可用 `CURRENT_POWER` 补差价**;买到的卡
经 `allocate_new_card(id, 2)` 进卡组。

## 1. 货币与资源(本次命名,GlobalsInner 块基址 `0x4cccdc`)

| 全局 | 地址 | = GlobalsInner+ | 语义 |
| --- | --- | --- | --- |
| `MONEY` | `0x4ccd34` | +0x58 | **金钱**(购卡货币;关卡掉落)|
| `CURRENT_POWER` | `0x4ccd38` | +0x5c | 火力(`/0x4ccd40`=档;**可在商店补差价买卡**,经 `GlobalsInner__spend_power`,不低于 ~1 档)|
| `LIFE_FRAGMENTS` | `0x4ccd4c` | +0x70 | 残机碎片(残机 HUD `FUN_00441f10(GUI, CURRENT_LIVES, LIFE_FRAGMENTS, LIVES_STOCK)` 中参)|
| `DAT_004ccd34..` 一族 | — | — | (难度=GlobalsInner+0 @ `0x4cccdc`;炸弹三元组见 cards-02)|

## 2. 待售卡生成(`AbilityShop__initialize` `0x4171B0`)

- 注册 `on_tick(0xc)` / `on_draw(0x51)`,建两个 `MenuSelect`(标签游标 +0xc、卡格游标 +0xe4)。
- **抽卡填列表**(`this+0xa30` 数组,数量 `this+0xec`):多次调
  **`CardShop__pick_weighted_random_offer`(`0x416F50`)**,各槽给一个**价格档区间** `[lo,hi]`(实测 (10,0xe)/(7,9)/(1,6)/(1,0xe))。
  - 抽法:遍历全卡 id(对 `ABILITY_MANAGER->field_0 + 0xc84 + id*4` 拥有计数数组),过
    **`CardData__is_available_for_difficulty`(`0x416E10`)** 难度闸 → 过价格档 `[lo,hi]`(`entry+0x10`)→
    过类别 `entry+0x14`(!=0 且 !=6)→ 去重 → 按 `entry+0x14`(权重)入池,**未解锁卡**(`SCOREFILE+0x5f588+id==0`)
    权重额外 ×5 → `Rng__rand_dword` 随机取一张。
  - 特殊卡:卡组里有 **`id=0x26`** → 解锁额外待售条目(initialize 里 3 处 `card_id==0x26` 分支)。

## 2b. offer 是"随机 + 保证"混合;卡也可经道具直接掉落(回答"通用卡/boss 卡必出?")

- **随机通用槽**:4 次 `pick_weighted_random_offer`(价格档区间)总会填几张随机卡 = "几个通用卡必出"的随机来源。
- **保证槽(initialize 两个大循环,遍历未拥有卡 `manager+0xc84+id*4==0`)**:
  - 循环1:难度可用 + `entry+0x14==0` → 必加。`+0x14==0` 的正是 **EXTEND/BOMB/PENDULUM/DANGO 等通用资源卡**
    → **"通用卡必出" ✅ 坐实**(以"未拥有"为前提)。
  - 循环2:`CardData__is_available_for_difficulty` 返回 **2**(即存档解锁位 `SCOREFILE+0x5f588+id==2`)→ 必加。
- **卡也能不经商店、直接掉落进卡组**:`ItemManager__on_tick__body` 道具 type **`0x10..0x13`** →
  `allocate_new_card(MGR, table_0x4b4020[type], 0)`(模式 0);实测这 4 类型给**固定通用卡** id 3/4/5/6
  (EXTEND2/BOMB2/PENDULUM/DANGO),**非 boss 专属**。
- ✅✅ **"本关 boss 卡必出"机制已破(一手反汇编证实)**。关键:`CardData__is_available_at_stage`(`0x416E10`)的
  返回值**不是布尔**(Ghidra 误标 `bool`,反编译显示 `return true` 是错的)。**反汇编实证**(地址见下):
  - `dmode==0` → `MOV EAX,1`(恒可用);
  - **`dmode∈1-5` 且 `CURRENT_STAGE==dmode` → `MOV EAX,0x2; RET`(返回 2 = 本关专属卡)**;
  - `dmode 6-10` 关卡区间命中 → 1(边缘 1/5 RNG);else → 解锁位(0/1)。
  - 证据:`0x416E2C MOV EAX,2`(dmode1+stage1)、`0x416E51`(dmode2)、`0x416E60/E6F/E7E`(dmode3/4/5)。
- **`AbilityShop__initialize` 两个保证循环 = 这两类的强制加入**:**loop1(`ret==1`)** 加 dmode0 恒可用通用卡
  (再过 `f14==0` 筛资源卡);**loop2(`ret==2`)** 加**当前关 boss 专属卡**。→ **boss 卡强制出现 = dmode 关卡门控 + loop2**。
- **dmode 1-5 卡 = 各关专属卡**(✅一手:`allocate_new_card` switch 给出 card_id→类,`is_available` 反汇编给出 dmode→关卡):
  | id | 类(allocate vtable)| dmode→关 |
  | --- | --- | --- |
  | 38(0x26)| `AbilityCardManekiInf` | 1面 |
  | 39(0x27)| `AbilityCardYamawaroInf` | 2面 |
  | 40(0x28)| `AbilityCardKiseruInf` | 3面 |
  | 51(0x33)| `AbilityCardMagatamaOpInf` | 4面 |
  | 52(0x34)| `AbilityCardCylinderInf` | 5面 |
  | 53(0x35)| `AbilityCardRiceballInf` | 5面 |
  - ⚠️ **证据分级**:类名是**物品代号**(招财猫/山童/烟管/勾玉/管/饭团),**非角色名**;binary **未**把它们标注为某 boss。
    "招财猫≈Mike、烟管≈Sannyo、勾玉≈Misumaru、管≈Tsukasa" 属**设定推断(lore),非一手**——代码只证到"**关卡专属**",
    证不到"**某 boss 的**"。要坐实需另找代码链(卡效果 vs boss 招式 / boss 敌人数据引用该 card_id)。**未做,标 🟡。**
  - 对比:别的卡确有**角色名类**(0x21 `Yuyuko`/0x1b `Koishi`/0x24 `Narumi`/0x25 `Pache`/0x2d `MikoFlash`/0x2e `Vampire`/7 `Mokou`),
    但这 6 张关卡专属卡全是物品代号。
- ✅ **机制已对抗复核通过**(2026-06-13,4 个独立只读 agent 各自重推):跳转表 `0x416f14` 把 dmode1-5 路由到 `MOV EAX,2`
  (实测可达、**非**死代码);loop1`CMP EAX,1`/loop2`CMP EAX,2` 均活;`0x4cccdc`=关卡(端关 `+=1` 并按 `*0xd4` 索引
  STAGE_DATA_TABLE,难度系**另一独立全局**)。Ghidra 的 `bool`/`return true` 确系反编译假象。
- 🟡 **与 wiki id 列表 `22,40,41,42,54,55` 的对账=开放项,别下"社区错了"的定论**:复核确认这六个 id **无论按 card_id
  还是按注册表数组下标**,五个是 `dmode=0`(恒可用)或 `dmode=12`(解锁位),**不会被 loop2 强制 per-stage**(仅 40 KISERU 真 dmode3)。
  **关键坑:注册表数组下标 ≠ card_id(从下标 8 起错位)**,疑为 wiki 编号对不上的根源。但**可能另有玩家图鉴号编号未提取,或 wiki 按
  主题精选而非按机制列**——故**只确证我们的机制,wiki 具体 id 对账不闭合、不外推为"社区有误"**(留用户/后续裁定)。
- 📌 教训(00-METHOD"一手到底"):**反汇编 `MOV EAX,2` 推翻反编译的 `return true`**——返回值语义务必看汇编,别信反编译的类型标注。

## 3. 关卡可用规则(`CardData__is_available_at_stage` `0x416E10`,原名 _for_difficulty,**订正**)
读 `zTableCardData+0x18`(关卡可用模式),**`CURRENT_STAGE` = `0x4cccdc`**(GlobalsInner field0;`end_stage` 自增它并索引
`STAGE_DATA_TABLE`,故是**关卡**非难度):
- **返回值(反汇编实证,非布尔)**:`0`→**1**(恒可用);`1..5` 且 `CURRENT_STAGE==dmode`→**2**(本关专属/boss 卡);
  `6..10` 关卡区间命中→1(边缘 `1/5` RNG);`0xb`:关卡 1-5;`0xc`:特殊;
- 其余/default:返回解锁位 `SCOREFILE + 0x5f588 + card_id`(0/1;`CardCollection__mark_obtained_and_notify` 置 1=购买/获得过)。
- **消费**:`initialize` **loop1 加 `ret==1`(通用),loop2 加 `ret==2`(本关 boss 卡)** —— 这是 boss 卡强制出现的真正路径。

## 4. 价格与购买(`AbilityShop__on_tick` `0x417CC0`,状态机 `this[0x38e]`)

- **定价 `CardShop__price_for_tier`(`0x416DD0`)**:价格表 **`0x4b35c4`** 按卡档位(`entry+0x10`)取金额;
  **卡组有 `id=0x27`(打折卡)→ 半价(`*5/10`)**。
- **买卡判定**(case 2 选中确认 `MENU_INPUT&0x80001`):
  `price = price_for_tier(offer+0x10)`;`if (MONEY < price)`:再判 `CURRENT_POWER-100 + MONEY < price` →
  买不起(音效 0x10);否则进"用 power 补差价"确认态(case 7);`MONEY >= price` → 直接确认态(case 6)。
- **执行购买**(case 6/7 选"是" `this[3]==0`):
  `AbilityManager__allocate_new_card(ABILITY_MANAGER, offer_card_id, 2)` 入卡组 + `FUN_00418de0(id,0)`;
  扣款:`price <= MONEY` → `MONEY -= price`;否则 `GlobalsInner__spend_power(&GlobalsInner, price-MONEY)` 扣 power
  (跨档则 `Player__repopulate_options_and_notify_cards`)。
- **`allocate_new_card` 模式**:`1`=存档重载(`reset_cards`)、**`2`=商店购买**、`3`=replay 复原(`sub_417880`)。

## 5. 持久化 & replay
- **卡组持久化在存档**(见 cards-01 §1d `reset_cards`:`SCOREFILE+0x5f608` card-id 字节数组 + `+0x5f678` 计数)。
- **解锁位**:`SCOREFILE + 0x5f588 + card_id`(每卡一字节;影响是否出现在商店 + 未解锁权重×5)。
- **`AbilityShop__sub_417880`(`0x417880`)= replay 存/复原卡组**(非购买):录制存当前牌组进 replay `+0xa64`;
  回放 `reset_cards` 后从 `+0xa64` card-id 数组 `allocate_new_card(id,3)` 复原 + 复原选中卡 + 各卡 `vtable+0x38`(set timer)/`+0x20`(on_load)。商店进/出时调。

## 6. zTableCardData 字段新解(注册表 `0x4c53c0`,stride 0x34)— 喂给 58 卡刻画
| 偏移 | 语义 | 来源 |
| --- | --- | --- |
| +0x00 | internal_name (char*) | ExpHP |
| +0x04 | card_id | ExpHP |
| **+0x10** | **价格档位**(索引 `0x4b35c4` 价格表 + 商店区间筛选)| 一手(`price_for_tier`/`pick_offer`)🟡 |
| **+0x14** | **权重/类别**(抽卡权重;商店要求 !=0 且 !=6)| 一手 🟡 |
| **+0x18** | **难度可用模式**(见 §3)| 一手 🟡 |
| +0x2c/0x30 | sprite_large / small | ExpHP |
> → 此前 `+0x08..0x2b` 全 `__unknown`,现解出 +0x10/+0x14/+0x18 三个。剩余仍未知,逐卡刻画时补。

## 7. 特殊卡 id 速记(meta 效果;⚠️ 常量是 hex,= 注册表十进制 id)
- `0x23` = **35 ROKUMON(六文)** — CardEirin 决死救命检查(`cards-01` §2c)。
- `0x26` = **38 MANEKI(招财猫)** — 商店**额外抽 3 张**(各价位全抽;§2 + wiki "携带招财猫额外抽三张")。
- `0x27` = **39 YAMAWARO(山童)** — **打折卡**:在卡组则商店**半价**(`CardShop__price_for_tier`,§4)。
> 完整 id→名 表见 `cards-03-card-registry-dump.md`。

## 8b. wiki 交叉验证(THBWiki,2026-06-13;一手 ✅ / 订正 / 仍开放)

| wiki 结论 | 一手核对 | 状态 |
| --- | --- | --- |
| 4 类卡:使用/装备/能力/**即时** | 我按 `flags(+0x50)` 只分了 3 类(主动0x8/装备0x40/其余),漏了**即时类**=资源卡(`cards-02`,获得即生效)| ✅订正(见 cards-01 §3)|
| C 用卡 / D 切卡 / 冷却 | `input&0x400`→c_press、`&0x800`→切卡、`recharge`(`cards-01` §2)| ✅ |
| 装备类=子机 | `on_power_level_change`→`Player__allocate_option`(`cards-01` §4)| ✅ |
| 3 随机卡:价位 [300-450]/[200-280]/[0-180] | `pick_weighted_random_offer(10,0xe)/(7,9)/(1,6)`,价格表 `0x4b35c4`:t10-13=300-450、t7-9=200-280、t1-6=50-180 | ✅逐字 |
| 招财猫额外抽 3 张(全价位)| 3 处 `card_id==0x26`(=38 MANEKI)各加一次 `(1,0xe)` 抽 | ✅逐字 |
| 5 固定卡 1,2,3,6,7 号 | initialize 两个保证循环 + `entry+0x1c`(f1c)=1 的资源卡复用;精确逐卡未完全闭合 | 🟡部分 |
| 该关专属卡必出 | **一手破**:`is_available_at_stage` 对 dmode∈1-5 且 `CURRENT_STAGE==dmode` 的卡返回 **2**(反汇编 `MOV EAX,2`),`initialize` loop2 强制加入。关卡专属卡(id→类,物品代号):38 Maneki/39 Yamawaro/40 Kiseru/51 MagatamaOp/52 Cylinder/53 Riceball | ✅✅机制;🟡"对应某 boss"=lore 非一手(类名是物品代号);wiki 引用 id 22,40,41,42,54,55 仅 40 重合 |
| 火力换钱:0.01 火力=1 金,透支后清零,加超 1.00 仍不够则不能买 | `on_tick` case2 判 `CURRENT_POWER-100+MONEY<price`;case6/7 `GlobalsInner__spend_power` | ✅ |
| 购买过一次的卡可作初始装备(即时/空白卡除外)| `CardCollection__mark_obtained_and_notify` 置 `SCOREFILE+0x5f588+id=1` | ✅ |
| 初始卡槽 1→2→3(Ex=3,练习=5)| `GameThread__end_stage` 操作 `SCOREFILE+0x5f678`(1→2→3)| ✅(数值档位待 dump)|
| 全收集成就(25 号)| `mark_obtained` 全 56 卡 → `TrophyNotice__award_trophy(0x1d=29)` | ✅(成就号 0x1d)|
| Ex 特有"勾玉"入关自动携带·不占初始槽 | 注册表 id51 MAGATAMA(dmode4);自动携带路径待验 | 🟡 |

## 8. Follow-up
- ⏳ 价格表 `0x4b35c4` 实际数值 dump(各档位金额)。
- ⏳ 商店 UI 状态机细节(case 0/1 入场动画、case 3 "buy all"、case 8/9)非核心,略。
- ⏳ `MONEY` 在关卡中如何掉落/累积(`ItemManager` 金钱道具)→ 并入资源经济 follow-up。
