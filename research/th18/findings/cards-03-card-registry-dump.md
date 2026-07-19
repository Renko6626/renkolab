# TH18 卡牌注册表 dump(58 项,一手)

> 注册表 `zTableCardData[]` @ **`0x4c53c0`**,stride **0x34**,共 58 项(`TableCardData__get` 线性查 card_id)。
> 本表为 dump 原始数据,供 58 卡逐张刻画(`cards-TODO-58card-characterization.md`)起手。字段语义见 `cards-04` §6。
> 适用:TH18 v1.00a。`internal_name` 从 `+0x00` 指针读;`id`=`+0x04`。

字段:`t10`=价格档位(`+0x10`,索引价格表 `0x4b35c4`)、`f14`=权重/类别(`+0x14`,商店随机要求 !=0 且 !=6)、
`dmode`=**关卡**可用模式(`+0x18`;`1-5`=限定该**关卡**出现,非难度,见 cards-04 §3)、`f0c`=类别/分页(`+0x0c`,0-4)、`f08`(`+0x08`,0/1)。
> ⚠️ 下表 `id` 为**十进制**。代码里的特殊卡常量是**十六进制**:`0x23`=35(ROKUMON)、`0x26`=38(MANEKI)、`0x27`=39(YAMAWARO)。

```
id  name           t10 f14 dmode f1c f08 f0c
 0  BLANK            0   0   11   0   0   2
 1  EXTEND           2   0    0   1   1   3   (残机)
 2  BOMB             0   0    0   1   1   3   (炸弹)
 3  EXTEND2          0   6    0   1   1   3   (掉落道具 type0x10)
 4  BOMB2            0   6    0   1   1   3   (掉落道具 type0x11)
 5  PENDULUM         0   0    0   1   1   3   (掉落道具 type0x12)
 6  DANGO            0   0    0   1   1   3   (掉落道具 type0x13)
 7  MOKOU           13   4    0   0   1   3
 8  REIMU_OP         8   3    0   0   1   1   (自机射击卡:子机)
 9  REIMU_OP2        9   1   12   0   0   1
10  MARISA_OP        8   3    0   0   0   1
11  MARISA_OP2       9   1   12   0   0   1
12  SAKUYA_OP        8   3    0   0   0   1
13  SAKUYA_OP2       9   1   12   0   0   1
14  SANAE_OP         8   3    0   0   0   1
15  SANAE_OP2        9   1   12   0   0   1
16  YOUMU_OP         8   3    0   0   1   1
17  ALICE_OP         9   3    0   0   1   1
18  CIRNO_OP         7   3    0   0   1   1
19  OKINA_OP         9   1    0   0   0   1
20  NUE_OP           7   2    0   0   0   1
21  ITEM_CATCH       3   3    0   0   1   2
22  ITEM_LINE        4   2    0   0   1   2
23  AUTOBOMB        11   2    0   0   1   2
24  DBOMBEXTEND      3   3    0   0   1   2
25  MAINSHOT_PU      6   3    0   0   1   2
26  MAGICSCROLL     10   3    0   0   1   2
27  KOISHI           3   2    0   0   1   2
28  MAINSHOT_SP      5   3    0   0   0   2
29  SPEEDQUEEN       4   3    0   0   0   2
30  OPTION_BR       11   1    0   0   0   2
31  DEAD_SPELL       3   2    0   0   0   2
32  POWERMAX        11   3    0   0   0   2
33  YUYUKO           8   1    0   0   0   2
34  MONEY            5   2    0   0   0   2
35  ROKUMON          5   2    0   0   0   2   (★0x23 CardEirin 决死救命检查)
36  NARUMI           5   4    0   0   0   2
37  PACHE            3   4    0   0   0   2   (Patchouli;__on_load 给 CURRENT_BOMBS)
38  MANEKI           5   2    1   0   1   2   (★0x26 招财猫:商店额外抽3张;1关专属)
39  YAMAWARO         2   2    2   0   1   2   (★0x27 商店半价折扣卡;2关专属)
40  KISERU           9   2    3   0   1   2   (3关专属;boss卡)
41  WARP            10   2    0   0   1   0
42  KOZUCHI          6   4    0   0   1   0
43  KANAME          12   2    0   0   1   0
44  MOON             8   2    0   0   1   0
45  MIKOFLASH       12   4    0   0   0   0   (Miko 主动卡)
46  VAMPIRE          8   2    0   0   0   0   (Remilia)
47  SUN             13   4    0   0   0   0   (Utsuho)
48  LILY            10   2    0   0   0   0   (LilyWhite)
49  BASSDRUM         5   2    0   0   0   0
50  PSYCO            6   2    0   0   0   0
51  MAGATAMA         8   4    4   0   0   1   (4关专属;Ex特有"勾玉",入关自动携带·不占初始槽)
52  CYLINDER         5   4    5   0   0   0   (5关专属)
53  RICEBALL         9   4    5   0   0   0   (5关专属)
54  MUKADE          10   3   12   0   0   2
55  MAGATAMA2        5   6    0   0   0   2
56  NULL             0   0    0   0   1   4   (菜单哨兵)
57  BACK             0   0    0   0   1   4   (菜单哨兵)
```

> 注:`internal_name` 是内部代号,非游戏显示名(显示名走另一张 string 表/ANM)。boss 卡按代号对应:
> MOKOU/NARUMI/PACHE(Patchouli)/KOISHI/YUYUKO/MIKOFLASH(Miko)/VAMPIRE(Remilia)/SUN(Utsuho)/LILY(LilyWhite) 等。
> `_OP`/`_OP2` = 各角色的两种自机射击(子机)卡。
