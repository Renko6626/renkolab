# 逆向工程发现 02:func_* / flags 社区复查(TH16 视角)

> 方法:第三轮 deep research(5 角度扇出 → 15 源 → 48 声明 → 验 25 → 确认 20/否决 5),
> 在 `01-runtime-semantics.md` 基础上**只记净增量**。日期 2026-06-08。
> 分级:✅高可信 / 🟡中可信(单源/推断) / ❌已否决 / ❓未解。
> 触发动机:动手反汇编 th16.exe 前,先确认社区没有现成的「索引→行为」表可省力。

## TL;DR — 结论:没有捷径,但拿到了强锚点

**`func_on_init/tick/hit` 的「索引→行为」映射,对包括 TH16 在内的任何一作都仍无公开破解**
(作者 Priw8 在 sht-webedit README 亲述 "documentation is yet to be made";issue #6 自 2018 起仍
open/help-wanted)。也**不存在抵达 TH13–19 的 ReC98 式反编译/符号工程**(ReC98 只到 TH05;thprac
只是内存补丁工具,零 SHT 逆向;Alex4386 的 TH17 gist 只有入口地址)。

→ **必须自己 Ghidra 反汇编 th16.exe**。但本轮确认了三条**可作锚点**的社区已验证结论(01 未收录):

## 1. func_* 的调用点/生命周期语义 ✅(ExpHP,th07–17)

不是「索引→行为」表,但**告诉我们每个 func 在引擎哪里被调用**——这正是 Ghidra 的下手点:

| 字段 | 何时被调用(引擎调用点) |
| --- | --- |
| `func_on_init` | 子弹/射击对象**创建时** |
| `func_on_tick` | 每帧 `Player::on_tick` 中 |
| `_old_on_draw` | `Player::on_draw` 中;**MoF/TH10 起约 90% 自动化,TH16 已不调用**(故名 `_old_`) |
| `func_on_hit` | **命中敌人时**(播放音效 / 如 UFO 早苗B 触发溅射弹) |

- 出处:sht-webedit issue #6 ExpHP 评论(2020-07-13)+ **已并入 PR #8 "Add funcs and second
  timer"**(2020-08-01 由 Priw8 合并,改了 struct_07–17.js + README)。可信:作者自评 "fairly
  certain",但已落地为代码,✅。
- ⚠️ 适用范围 **th07–th17**,**不含 TH18/19**。
- **对 Ghidra 的意义**:在 th16.exe 里找 `Player::on_tick`、命中处理路径里**通过 func_* 索引发起的
  间接调用 / switch 分派**,顺藤摸到跳转表 → 逐个反编译命名,产出「索引→行为」表。

## 2. flags 段 = load-time 被替换为函数指针的派发槽 🟡(RUEEE,单源)

- RUEEE(issue #6, 2019-08-06)原话:flags **不是 word 而是 dword,共 12 个**;**读 .sht 时每个
  flag 被替换成特定函数(通常 thiscall)**;**ZUN 只用前 4 个**;**枚举值逐 flag 逐作不同**——
  **TH15**:flag1∈{1..5}、flag2∈{1..4}、flag3∈{1,2}、flag4∈{1..6}。
- 可信:🟡 单贡献者、单 issue;Priw8 致谢过 RUEEE,ExpHP 跟进细化(非反驳)。**值含义→行为仍未公开**。
- ⚠️ **与我方 `struct_16.js` 冲突,须在 th16.exe 自证**:struct_16.js 记 `flags_len=0x20`(32 字节)、
  `flag_size=2`(→ 16×int16);RUEEE 说"12 dword"(48 字节)。两者对不上(也许 RUEEE 指别版本,或
  sht-webedit 的 schema 仅按字节数留位、未细分)。**TH16 的 flags 实际结构以反汇编为准。**
- **对 Ghidra 的意义**:找**读 SHT 后把 flags 区各槽替换成函数地址**的加载例程(典型:循环写函数
  指针 / 按枚举值查表填指针)。TH15 的枚举基数(5/4/2/6)给出**预期跳转表条目数**做交叉验证(但**别
  假定 TH16 沿用 TH15 编号**)。

## 3. 部分标量字段已确证,可从反汇编清单里排除 ✅/🟡

- ✅ **rate2/delay2(= 120 帧计时器)**:用于发射间隔 >128 帧 / 非 15 的因子的射击;因 rate/delay 走
  15 帧计时器,rate2/delay2 取 120 的因子。**TH16 的「夏副季节 sub-shot」计时就是走 rate2/delay2,
  不是特殊 func/flag**(出处:RUEEE+ExpHP)。→ **部分回答开放问题 Q4**:副季节的*计时*已知;副季节的
  *行为分派*仍在 func_*/flags 里,未解。
- 🟡 `unknown_sht_int16` = 发射音效 id(-1=无)(Priw8 自评 confirmed,但本轮一条等价声明 0-3 被否,
  降级🟡待 Ghidra 复核)。
- 🟡 `unknown_1`/`max_dmg` = 单帧对单体最大伤害(DDC/**TH14** 起,亦影响 bomb)。
- 🟡 `unknown_0`/`SA_power_divisor` = 仅 SA/TH11 的涨 power 除数(f=100/unknown_0,为 0 会崩)。
- 📝 勘误:01 与背景把 DDC 当 TH13,**DDC 实为 TH14**(TH13=神灵庙)。

## 4. 明确否决(别当线索)❌

- ❌ 「post-option 字节 = 激光/option 分配 flag(TH15 取 2 / TH14 取 3,灵梦A御币)」——本轮 0-3 否决。
- ❌(沿用 01)「PCB 0x28 枚举(1=寻的/2=寻的+加速/3=加速/4-5=激光)是 func_* 前身」——不成立。
  PCB 的「索引→行为」表(Mddass)**只证明这种表的形态在 ZUN 早期 shot 码里存在过**、给出可参考的行为
  类别(homing/accel/laser)用于在 th16.exe 里"找什么",**不能外推数值到 TH16**。

## 5. 仍敞开 / 下一步需 Ghidra 解的(本轮未消除)

1. TH16 的 `func_on_init/tick/hit` 各「索引→行为」具体表。
2. TH16 的 flags 实际结构(dword 数、是否函数指针派发)与各槽含义;TH15 枚举是否沿用到 TH16。
3. TH16 季节/副季节的**行为选择**(非计时)在 func_*/flags 还是引擎硬编码。
4. 🟡 TH16–19 是否共用 func_* 编号(ExpHP 文档止于 th17)——若是,一次反汇编可覆盖多作,值得先验。

## 6. 未尽的检索面(本轮 web 未能穷尽)

私有 Discord 存档、Bilibili/NicoNico 技术向视频、2chan/贴吧/NGA mod 帖、danmakufu 移植者笔记——
本轮只覆盖公开 GitHub/wiki/web。若动手前想再省力,可定向搜这些,但**预期收益低**,不应阻塞反汇编。

## 来源(本轮新增/复核)

- Priw8 sht-webedit README + **issue #6**(ExpHP 调用点、RUEEE flags 模型)+ **PR #8**(已合并):
  <https://github.com/Priw8/sht-webedit/issues/6> · <https://github.com/Priw8/sht-webedit/pull/8>
- 否定证据:nmlgc/ReC98(止于 TH05)、touhouworldcup/thprac(内存补丁,无 SHT)、
  delthas/touhou-protocol-docs(仅绯想天则网络协议)、Alex4386 TH17 gist(仅入口地址)、
  Mddass 规范(仅 TH07/12/13)。
