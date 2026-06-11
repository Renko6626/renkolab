# 逆向工程发现 07:TH16 SHT shooterset 组织 + shooter 主次结构

> 方法:Ghidra(ghidra-re MCP)反编译 `Player__do_shooting`(ExpHP 名)@ **0x445470**(用户自有
> th16.exe)+ 本地解析 pl02.sht(10 set / 80 shooter)逐字段印证。日期 2026-06-11。
> 分级:✅高 / 🟡中 / ❓未解。**仅 TH16(天空璋)**。承接 03(func_* 跳转表)、05(字段图)。
> 回答的问题:**一个 .sht 里那么多 shooter,谁是主弹谁是子机弹?10 个 shooterset 怎么按火力/聚焦选?**

## 0. 一句话结论

每个 .sht 的 shooter **不是平级的**。两层主次:
1. **shooterset 层**(选哪一组):`set = 火力档 + (聚焦 ? 火力档数+1 : 0)`。pwr_lvl_cnt=4 →
   **非聚焦 = set 0–4、聚焦 = set 5–9**(各 5 档火力)。
2. **组内 shooter 层**(一组里同时发哪些):**前若干个 = 主弹(自机本体,`opt=0`)**,
   **其余 = 子机/option 弹(`opt=1..4`,从子机位置发)**;子机数随火力增长。
3. 另有**第二条发射循环 = 副/季节弹**,取自**副 .sht**(plXsub),按"季节能量"选档。

## 1. 选择逻辑:`Player__do_shooting` @ 0x445470 ✅(ExpHP 名 + 一手反编译)

```c
set = CURRENT_POWER / POWER_PER_LEVEL;                 // 火力档(power 存 ×100,POWER_PER_LEVEL=100)
if (this+0x165c8 != 0)                                  // 聚焦标志(见 §4)
    set = set + 1 + *(int*)(sht_base + 0x20);           // 聚焦 → 偏移 (pwr_lvl_cnt + 1)
shooter = *(char**)(sht_base + 0x190 + set*4);          // sht_off[set] → 该 shooterset 首 shooter
while ((int8)shooter[0] >= 0) {                         // 遍历组内 shooter(byte0<0=组终止)
    // 发弹计时(见 05 字段图):
    if (shooter[0x26] == 0)  fire = (frame_main  % shooter[0x00]) == shooter[0x01];   // 主计时器
    else                     fire = (frame_120   % shooter[0x26]) == shooter[0x27];   // 备用 120 帧计时器
    if (fire) Player__shoot_one_bullet(this, (set<<8) | idx_in_set, ...);             // ★ packed id
    shooter += 0x58; idx_in_set++;
}
// —— 第二个循环:副/季节弹,来自副 .sht ——
season_lvl = 数 CURRENT_SEASON_POWER 越过 SEASON_POWER_LEVEL_REQUIREMENTS 几档;
shooter = *(char**)(sht_base2 + 0x190 + season_lvl*4);  // sht_base2 = player+0x2c78c = 副 .sht
while (...) { 同样计时; if(fire) shoot_one_bullet(this, ((season_lvl|0x100)<<8)|idx, ...); }  // ★ 0x100 位=副
```

要点:
- **shooterset 索引公式**:`set = power_lvl + (focus ? pwr_lvl_cnt+1 : 0)`。pwr_lvl_cnt=4 →
  非聚焦 set 0–4、聚焦 set 5–9 ✅。
- **packed id** `(set<<8) | idx_in_set` 写入子弹槽 `+0xac`;副弹再或上 `0x100`。这正是 `05` 里
  `slot+0xac` 的来源,也是 hit3/hit4(`0x446e20/f80`)用 `uVar1 & 0xf0000` 区分主/副 .sht、用
  `(uVar1>>8)`/`(uVar1&0xff)` 反查 shooter 读 dmg 的依据 → **整条"发射→命中反查"链闭合** ✅。
- **主 .sht 用本体火力档,副 .sht 用季节能量档**(两套独立计数器)。

## 2. 组内 shooter 的主次:主弹 vs 子机弹 ✅

以 pl02(琪露诺/夏)逐字段实测,组内 shooter 干净分两类(字段名见 `05` §2):

| 类别 | 判据(实测) | off | anm | speed | fire_rate | 角色 |
| --- | --- | --- | --- | --- | --- | --- |
| **主弹** | 每组**前 2 个**,`opt=0` | `(±10, −8)` | 0 | **24**(快) | 3 | 自机**本体**两道竖直弹(`ang=−90°`),伤害略高(set0/5 满血时 dmg 16 vs 14) |
| **子机弹(副/option)** | 其余,`opt=1..4` | `(0, 0)` | 1 | **8**(慢) | 5 | 从**子机/option** 位置发(`opt` 选第几个子机,坐标来自 header option_pos 表 @0x40);扇形角度铺开;带 `fr2`(120 帧计时) |

- **`opt`(shooter +0x20)= 子机选择**(`05`:0=本体默认,≠0 索引 option 表)。pl02 实测:
  火力 1 → 出现 `opt=1`;火力 2 → 加 `opt=2`;火力 3 → 加 `opt=3`;火力 4 → 加 `opt=4`。
  **= 火力越高,激活的子机越多** ✅。每个子机带 2–3 个不同角度的 shooter(它那一簇扇形)。
- 主弹 `off=(±10,−8)` 是相对自机的固定偏移;子机弹 `off=(0,0)` 因为位置由 option 表给。
- 聚焦 vs 非聚焦的**几何差**(自证聚焦标志):pl02 满火非聚焦(set4)子机角度 −30°…−150°(**宽扇**),
  满火聚焦(set9)−60°…−120°(**收窄前倾**)——经典"聚焦=集中火力 / 非聚焦=广角"。

## 3. pl02 shooterset 全貌(worked example)

| set | 选中条件 | shooter 数 | 构成 |
| --- | --- | --- | --- |
| 0 | 非聚焦 · 火力0 | 2 | 仅主弹×2 |
| 1 | 非聚焦 · 火力1 | 6 | 主弹×2 + 子机1(×4) |
| 2 | 非聚焦 · 火力2 | 8 | 主弹×2 + 子机1,2 |
| 3 | 非聚焦 · 火力3 | 10 | 主弹×2 + 子机1,2,3 |
| 4 | 非聚焦 · 火力4 | 14 | 主弹×2 + 子机1,2,3,4(宽扇) |
| 5–9 | **聚焦** · 火力0–4 | 2,6,8,10,14 | 同上但角度收窄前倾 |

> 注:主弹两道在**所有 set**里几乎一字不差(只满血档 dmg 16 vs 升级后 14)——主弹是"底火",
> 火力成长几乎全靠**逐档增加子机簇**。这套"前 N 个=本体主弹、其余=按 opt 分组的子机弹、按火力档
> 增减子机、聚焦/非聚焦各一份"的结构,**是 TH16 自机 .sht 的通用骨架**(其余角色同理,几何/anm 不同)。

## 4. 可信度 / 待复核

- ✅ 一手:选择公式、packed id、主/副双循环、组内 opt 分组、聚焦偏移——全来自 `0x445470` 反编译 +
  pl02 字段实测,且 `0x445470` 是 ExpHP 命名函数(社区确认其身份)。
- 🟡 **聚焦标志 = `this+0x165c8`**:由"它非零→选第二组 set 5–9"+ 几何上第二组明显更集中**强烈支持**
  是聚焦位,但该字段本身的写入点本篇未单独追(故标 🟡,非 ❓)。
- ❓ `fr2`/`start_delay2`(120 帧计时)在子机弹上的精确节奏未逐发对时(机制见 `01` §3)。
- 适用版本:**仅 TH16**;`pwr_lvl_cnt`、聚焦偏移、option 表布局他作可能不同。

## 5. 对 IDE / 编辑的指导

- SHT 编辑器应把 shooterset **按 (火力档 × 聚焦) 二维呈现**,而非平铺 10 组;组内按 `opt` 把
  shooter 归类为"本体主弹 / 子机#N 弹",让用户知道改的是哪一束。
- 改行为(如把 pl02 改 homing)时可**按主次分别处理**:只改子机弹(`opt≥1`)= 副火力寻的、主弹保持直线;
  或反之。详见与本篇配套的 homing 实验(`files/pl02_homing.sht`,当前是**全 shooter** 改寻的)。

## 来源
- 一手:th16.exe 反编译 `Player__do_shooting@0x445470`(ExpHP 名);pl02.sht 本地解析(版权不入库)。
- 交叉:`05-*.md`(shooter/header 字段图)、`03-*.md`(func_* 行为)、`01-*.md` §4(社区 power/聚焦模型)。
