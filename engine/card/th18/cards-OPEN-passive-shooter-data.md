# 【开放问题·搁置】被动/装备卡的支援射击 shooter 数据存在哪?
> **版本**：TH18 v1.00a（`th18.exe`）。本文裸地址默认属该版本；引用其他版本须写成 `th16:0x…`。
>

> 状态:🟡 **搁置(park)**,留给后续独立 deep research(社区结果 + 一手反)。
> 本文只钉住"问题 + 已知一手线索 + 假设",**不下结论**。证据链纪律见 `../METHOD.md`。
> 适用版本:TH18(東方虹龍洞)v1.00a,`th18.exe`(database_id `th18`)。

## 问题(为什么要留口子)

TH18 的**装备/射击卡**(`CardReimu1/2`、`CardMarisa1/2`、`CardSakuya1/2`、`CardSanae1/2`、`CardYoumu`、
`CardAlice`、`CardCirno` …)每张生成一个**子机(option/familiar)**,每射击帧用一张 **.sht shooter 表**开火。
每张卡的 shooter 表用一个**逐卡烘死的索引**选取(见下表)。

**矛盾点**:索引能到 `0x12`(18)以上、且 58 张卡里相当一部分各有一套支援弹幕;但 `th18.dat` 解包出来
**只有 `pl00`–`pl03` 四个 .sht 文件**(对应 4 个角色,不是大量多样的 .sht)。→ 那这些**逐卡的额外 shooter
表到底存在哪**?是塞进了那 4 个 pl 文件里的一个大数组,还是在 exe 里别处?**目前未定,搁置。**

## 已知一手线索(th18.exe,可信)

- **取表点(一手)**:`Player__tick_shooters_for_ability_card`(`0x40A9C0`)与 `Player__tick_shooting_state`
  (`0x45EA00`)都按
  ```c
  shooter_table = *(char**)( *(int*)(PLAYER_PTR + 0x47940) + 0xe0 + index*4 );
  ```
  取一张 shooter 表;表项 stride **0x5c**,符号位(`*ptr < 0`)终止 —— 与 TH16 SHT shooterset 同形
  (TH16 stride 0x58,见 `../engine/sht/th16/07`)。
- **逐卡索引(一手,`*__on_shoot`/vtable 0x1c 的 override)**:
  | 卡 | index(传给 `tick_shooters_for_ability_card` 的 param_4)|
  | --- | --- |
  | CardReimu1 | `0xa` (10) |
  | CardReimu2 | `0x12` (18) |
  | CardMarisa1 | `0xb` (11) |
  | CardSakuya1 | `0xc + (聚焦?1:0)` → 非聚焦 `0xc` / 聚焦 `0xd`(聚焦位 = `*(PLAYER+0x476cc)`)|
  | …(其余 ~12 张 `*__on_shoot` 卡未逐一取,call 点见 xrefs to `0x40A9C0`)| 待取 |
- **`PLAYER + 0x47940`** = player 的"射击/SHT 数据"指针(基础自机 shot 也用同一指针的 `+0xe0+idx*4`)。
  **未确认它指向什么**:是不是加载进来的 `pl0X.sht` 映像?`+0xe0` 是不是一张 shooter-表指针数组?**这是缺口核心。**

## 待查假设(deep research 时逐个验)

1. **「4 个 pl 文件其实很大,装了全部卡的 shooter 表」**:`pl0X.sht`(每角色一份)内部 `+0xe0` 是一个
   **按 index 寻址的 shooter-表指针数组**,把该角色所有可用卡的支援弹幕都打包进去 → 解包只见 4 文件但内容很全。
   *验法*:`set_type zPlayer* @ PLAYER`,反 player shot 加载路径(找谁写 `+0x47940`),看它读哪个 .sht、文件多大、
   `+0xe0` 数组长度;再对 `pl00.sht` 做字节布局,数 shooterset 个数是否 ≥ 0x13。
2. **「shooter 表在 exe 内嵌(.rdata),不在 .sht」**:`+0x47940` 指向 exe 内静态结构。
   *验法*:`get_xrefs_to` 写 `+0x47940` 的点;若源是 exe 全局而非堆分配的 .sht 缓冲,则成立。
3. **「index 跨"角色×卡"复用同一张表」**:不同卡可能共用 shooter 表,索引数 < 卡数。*验法*:统计所有 `*__on_shoot` 的
   index 取值集合大小。

## 后续计划(用户拍板)

- 计划单开一次 **deep research**:查社区(sht-webedit / thpatch / Priw8 逐版本 struct / pytouhou)对 **TH18 pl 文件
  与卡牌支援弹幕**的已知结论,叠加一手反(验上面 3 个假设)。
- 在此之前**不在主线纠缠这条**;主线先把卡牌核心流程(分配/选中/tick、c_press/充能、被动 vtable 接口)做完。

## 交叉引用
- 装备卡子机模型(一手,已验):见即将落地的 `cards-01-*`(`on_power_level_change`→`Player__allocate_option`→
  子机存卡+0x54;`on_tick_shooters`(0x1c)→ `tick_shooters_for_ability_card`)。
- SHT shooterset 同形参照:`../engine/sht/th16/07-shooterset-organization.md`(TH16,待验是否跨作共用编号)。
