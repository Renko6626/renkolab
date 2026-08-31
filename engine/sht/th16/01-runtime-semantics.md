# 逆向工程发现 01:SHT 运行时语义

> 方法:deep research(多源检索 + 3 票对抗验证,52 条声明→验 25→确认 22/否决 3)+ 本地
> `vendor/` 源码交叉核对。日期 2026-06-08。
> 结论分级:✅高可信 / 🟡中可信(单源或推断)/ ❌已否决 / ❓社区未解。

## TL;DR — 残酷的现实

**SHT 的运行时语义,社区只逆向了一半。** 字节布局清楚(sht-webedit),但**那些"控制实际行为"
的字段——`func_*` 行为函数索引、`flags` 段、各种 `unknown_*`——至今没有任何已发布的逐版本
含义表**。连格式的逆向者本人(Priw8)都在 README 里写 "who knows" 和 TODO。要彻底搞懂,只能
对每个游戏 exe 做 IDA/Ghidra 反汇编——目前没人公开做过这件事。

**对 IDE 的直接含义**:这些字段短期内**只能当作"带语义标签位的不透明整数"原样保留**,并把
基础设施建成"日后能挂一张逐版本名称表"的样子。不要试图现在就解释它们。

## 1. 行为函数索引 func_on_init/tick/draw/hit ✅(存在)❓(含义未解)

- ✅ 确认:它们是**指向 exe 里硬编码函数的索引**,实现寻的、溅射伤害、命中音效、激光等行为。
  README 原文:"sets index of hardcoded functions that implement behavior like homing, splash
  damage, hit sound effects, etc. **(documentation is yet to be made). Different games have
  different functions.**"
- ❓ **没有任何已发布的"索引→行为"逐版本映射表**。touhouwiki(Mddass)、pytouhou、thpatch 都没有。
- TH19(獣王園 UDoALG)把这块重排成 4 个 `func_?` int16(语义更不明)。
- 🟡 唯一的旁证来自 pytouhou 对 **Gen-1(TH06/07/08)** 的实现,但那是**完全不同的旧机制**(见 §4),
  不能外推到 TH15-19。

> 行动:在数据模型里把 `func_*` 存为命名整数字段;预留一个 `func_semantics`(版本→索引→名称)的
> 外部映射表挂载点(类比 ECL 的 eclmap 语义层),等社区/我们自己反汇编出表再填。

## 2. flags 段 + unknown 字段 ❓(社区公开未解)

- ✅ 确认:`flags`(TH14-18 共 0x20 字节,TH19 扩到 0x3c)**连逆向者都没搞懂**。README:"flags -
  mysterious extra fields, seldom used, who knows";TODO:"find out what the unknown values do";
  仓库 Issue #6 "Unknown values" 佐证。
- ✅ 这不是新作独有:**连 PCB(TH07)规范都留着 unknown1..unknown6 没标注**(pytouhou TH07 doc:
  "uint16_t unknown1; // Seems ignored"、"float unknown2; //TODO")。
- main 头部 `unknown_2..unknown_10`(int32)、shooter 里 `unknown_sht_float` / `unknown_sht_byte_*`
  同样无文档。

> 行动:`flags` 当整数数组无损保留;`unknown_*` 保留原值。**回写时务必字节级还原**,否则可能破坏
> ZUN 解析器假设。

## 3. 发弹计时模型 ✅(已确认)

各版本计时器粒度(README,3-0 确认):

| 游戏 | 计时器 | "整除"才均匀发射的 fire_rate |
| --- | --- | --- |
| PCB(TH07) | 60 帧 | 60 的因子(1,2,3,4,5,6,10,12,15,20,30,60) |
| IN–DDC(除 MoF) | 15 帧 | 1,3,5,15 |
| MoF(TH10) | 16 帧 | 1,2,4,8,16 |
| **LoLK 起(TH15+)** | 主计时器仍 15 帧;新增 `fire_rate2/start_delay2` 走 **120 帧** | — |

- ✅ **LoLK 起的 `fire_rate2`/`start_delay2`**:一旦设置 `fire_rate2`,原 `fire_rate/start_delay`
  被忽略。用 120 帧计时器的射击"famously have rare bugs that can cause them to stop firing"。
- ❓ **这个"卡住不发射"bug 的代码级根因没有任何来源给出**(整数溢出?计时器重置失步?取模相位
  冲突?均未证实)。

> 行动:UI 在 fire_rate 字段旁按版本提示"建议取计时器因子";在 `fire_rate2` 字段旁给"120 帧计时器,
> 有偶发卡弹风险"的警告。计时器帧数做成版本元数据。

## 4. shooterset 选择 + Gen-1 发弹模型 ✅/🟡

- ✅ **TH10+**:shooterset 按 power 等级组织成"聚焦/非聚焦"成对;头部带 `pwr_lvl_cnt`、每个 power
  的 option 位置、shooterset 偏移数组。`pwr_lvl_cnt=4` → 10 个 shooterset(含 0-power 那组)。
- 🟡 **Gen-1(TH06/07/08)pytouhou 实现**(二手,仅旧引擎):
  - 选 shooterset:`sht = focused_sht if focused else sht`,再取 `sht.shots` 里**大于当前 power 的
    最小阈值**键(power 阈值字典)。
  - 发弹判定:`if (fire_time + shot.delay) % shot.interval != 0: continue` —— `interval`≈fire_rate
    (周期),`delay`≈start_delay(相位偏移)。⚠️ 字段名是 pytouhou 的 `interval/delay`,与 thtk 的
    `fire_rate/start_delay` 的对应是分析者的合理推断(2-1)。
  - **Gen-1 的 `type` 字段是行为选择器**:`3`=自机激光(仅 `fire_time==30` 触发,复用 `delay` 当
    激光槽索引)、`2`=加速弹、`1`=寻的(pytouhou 标 TODO 未实现)、其他=直线弹。这是"行为分派"的
    早期雏形,但**与 TH15-19 的 func_* 不是一回事**。

## 5. PCB 旧布局 vs 新作模型 ✅(重要区分)

- ✅ **PCB(TH07)是另一套机制**,**没有 func_on_* 字段**:行为是扁平的逐弹字段(如 homing 布尔)+
  一堆 unknown,头部用 `{uint32 offset, uint32 power}`(thsht_offset_t)数组映射 power,以
  `0xffff/0xffff` 哨兵终止。
- ✅ **Mddass touhouwiki 规范只覆盖 TH07/TH12/TH13**——**没有 TH14-19 的任何布局**。新作只能靠
  sht-webedit。
- ❌ **被否决(0-3)**:"PCB 的 0x28 int32 枚举(1=Homing,2=Homing+accel,3=Accel,4/5=Laser)是
  func_on_* 的前身"——这个桥接说法**不成立**。PCB 枚举只是 PCB 自己的东西,别拿它推断新作语义。
  (相关的 0x24/0x2C/0x30 枚举说法同样 0-3 否决。)

## 6. sht-webedit 覆盖范围 + shmupcc 真相

- ✅ **部署站 `priw8.github.io/sht-webedit/` 的版本选择器到 v19(UDoALG/獣王園)**,含 TH14/14.3/
  15/16/16.5/17/18/18.5/19。**GitHub README 是过时的(只到 TH18)**——以部署站和 `vendor/` 源码为准。
- 🟡→✅ **shmupcc 格式**:deep research 因仓库无 README 无法确认其"大端/float64"。**但我已在
  `vendor/shmupcc-sht/src/shmupcc.ts` 一手核对:确实是大端 + FLOAT64**(`Endianess.BIG_ENDIAN`,
  header 的 hitbox/grazebox/itembox 全 `DataType.FLOAT64`)。它是一个**归一化/独立格式**(很可能
  对应 "Shmup Creator" 引擎或统一中间表示),`versions.ts` 目前只注册了 `"shmupcc"` 这一个,**不含
  真实东方逐版本 reader**。详见 `docs/sht-webedit-and-shmupcc-analysis.md` §4。

## 7. 关键结论 → 落到 IDE 设计

1. **可解释的字段**(发弹/判定/位置/引用):`fire_rate(2)`、`start_delay(2)`、`off_x/y`、
   `hitbox_x/y`、`angle`、`speed`、`dmg`、`option`、`anm`、`anm_hit`、`sfx_id`、`pwr_lvl_cnt`、
   option 位置——这些可以做友好 UI + 校验 + 提示。**先把编辑器价值建立在这批字段上。**
2. **不可解释的字段**(`func_*`、`flags`、`unknown_*`):当不透明整数无损保留,字节级回写;预留
   逐版本语义表挂载点。**这是诚实且安全的做法,不要假装懂。**
3. **计时器帧数**做成版本元数据,驱动 fire_rate 提示与 fire_rate2 卡弹警告。
4. **若要真正解开 func_*/flags**,唯一路径是对各游戏 exe 做 Ghidra/IDA 反汇编——这是一个**独立的、
   重量级的后续研究项**,不应阻塞 IDE 的只读/可编辑基础能力。

## 8. 仍然敞开的问题(社区级未解)

- `func_*`(及 TH19 的 4× `func_?`)逐游戏的"索引→行为"映射(需反汇编 exe)。
- `flags` 段(0x20→TH19 的 0x3c)的位/字段含义,以及 TH19 为何扩容。
- LoLK 120 帧计时器卡弹 bug 的代码级根因。
- shmupcc 的大端/float64 归一化格式到底对应哪个引擎、如何映射回各版本东方 struct。

## 来源

- Priw8 sht-webedit(一手,新作权威):<https://github.com/Priw8/sht-webedit> +
  部署站 <https://priw8.github.io/sht-webedit/> + Issue #6
- pytouhou(Gen-1 引擎实现/文档,二手但严谨):<https://pytouhou.linkmauve.fr/doc/07/sht.xhtml> +
  player.py/.pyx
- Mddass touhouwiki 规范(仅 TH07/12/13):
  <https://en.touhouwiki.net/wiki/User:Mddass/Touhou_File_Format_Specification/SHT>
- 本地一手核对:`research/sht/vendor/shmupcc-sht/src/shmupcc.ts`(大端/float64 已证实)
