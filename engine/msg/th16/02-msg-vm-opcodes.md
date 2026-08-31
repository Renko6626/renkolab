# 02 · TH16 stage-MSG opcode → 行为表(对话 VM 指令集)

> 适用:**TH16《鬼形兽》`th16.exe` v1.00a**,**仅"关卡内对话 stage MSG"**(`stXXy.msg`)。
> ⚠️ **结局 / staff roll / mission.msg 是另一套指令集**(ExpHP 原话:"Ending MSG and staff MSG files use a
> different set of instructions … `mission.msg` is a completely different format")——见 `01` §5,未在本表内。
>
> **本表是三方交叉结果,可信度高**:
> - **ExpHP `truth`**(权威编译器)`src/core_mapfiles/msg.rs` → **指令签名 + 逐版本编号**(MSG_10_185 链)。
> - **ExpHP `thpages`**(指令参考站)`js/tables/reference/msg.ts` → **指令名 + 行为描述**(本表"ExpHP 行为"列)。
> - **我们一手反编译** `GuiMsgVm::run`(0x42A1D0)→ **exe 实证**(本表"exe 实证"列,带 case/地址)。
> 三者一致标 ✅;仅 ExpHP 双源、我们未逐条验 exe 的标 🟡。
> 出处与许可:ExpHP/truth、ExpHP/thpages(GitHub,GPL 系)。本表为**摘要+交叉注**,非原文照搬;详细 prose 见
> <https://exphp.github.io/thpages/> 的 MSG 页。

## 0. TH16 指令集怎么来的(版本继承链)

stage MSG 自 TH10 起是同一套,逐版本增删。TH16 = `TH14 集` + TH16 新增 {33,34,35},其中 TH14 在 TH13 上
override 了 5/8/14/20/24 并加 32,TH11 在 TH10 基础上**在 9 处插了一条**(导致 TH10 的 9..23 整体右移一位)。
(链:TH10→[TH11 插位]→TH12→TH128→TH13→TH14→[TH15=TH14]→**TH16**)。最大 opcode = **35 (0x23)**,
正好等于 `GuiMsgVm::run` switch 的上界 `case 0x23` —— **范围一手吻合 ✅**。

## 1. 字符串编码(文本指令 `m` 的载荷)

文本指令(15/16/17 等签名带 `m`)的字符串:**Shift-JIS** → 加 null → null-pad 到 4 字节倍数 →
**自 TH09 起整体 XOR 一个"加速掩码"**(初值 `0x77`、初速 `0x07`、加速度 `0x10`,逐字节推进,**含 padding**)。
**自 TH12 起有 furigana(注音)bug**:含注音的指令之后,**下一条**指令的字符串解码后会在 null 之后**带上
前一条注音的密文残留**(ZUN 编译器 bug)。→ IDE 解析 `.msg` 文本时必须实现这套解码 + 容忍 furibug。
(出处:thpages `getMsgTableText`;TH16 属此分支。)

## 2. opcode → 行为表(TH16,0..35)

> 列:opcode · ExpHP 名(ref) · 签名(truth)· ExpHP 行为(摘要)· exe 实证(我们 `run` 内 case/地址)· 可信度。
> 签名记法:`S`=int32, `f`=float, `m`=掩码字符串(文本), `_`=被忽略的 dword, `ss`/`SS`=两个参数。

| op | 名(ExpHP ref) | 签名 | ExpHP 行为(摘要) | exe 实证(case @0x42A1D0) | 可信 |
| --- | --- | --- | --- | --- | --- |
| 0 | end | — | 终止脚本(不杀引擎) | case 0 → `return 0xffffffff`(触发拆 VM) | ✅ |
| 1 | show-player | `_` | 自机立绘出现 | case 1:create_effect 自机/敌方 face(读 instr+4) | ✅ |
| 2 | show-enemy | `S` | 敌方立绘出现(who) | case 2:按 stage 文件表建敌方 face | ✅ |
| 3 | show-textbox | — | (ExpHP 名)显示文本框 | **`run` 无 case 3 → TH16 中为 nop/历史遗留**(盲验证实) | 🟡 nop |
| 4 | hide-player-single | — | 隐藏自机立绘 | case 4:interrupt face 槽 +0x40 | ✅ |
| 5 | hide-enemy | `S` | 隐藏(某)敌方立绘 | case 5:interrupt +0x44[i] / +0x68 | ✅ |
| 6 | hide-textbox | — | 隐藏文本框(连立绘文字全清) | case 6:interrupt 0x58/5c/60/64 + unload 0x6c | ✅ |
| 7 | focus-player-single | — | 标记**自机**在说话(左侧布局) | case 7:active_side=0 + 立绘高亮/变暗调度 | ✅ |
| 8 | focus-enemy | `S` | 标记**某敌方**在说话(右侧布局) | case 8:active_side=1 + 同上 | ✅ |
| 9 | focus-none | — | 清除"谁在说话"高亮 | case 9:active_side=0 + 写立绘位置 | ✅ |
| 10 | skippable | `S` | 置布尔位:=1 时文本可快进 | case 10:`flags ^= (arg^flags)&1`(读 instr+4) | ✅ |
| 11 | **pause** | `S` | **等玩家按射击键**(最多 max 帧)推进 | case 0xb:pause_timer + INPUT shot/bomb 推进(13 帧节流) | ✅ |
| 12 | **ecl-resume** | — | **唤醒等待 MSG 的 ECL 脚本**(放行 `519 dialogWait`;常用于让 boss 起飞) | case 0xc:`vm[0x18c]=1` 一帧脉冲 ↔ dialogWait 读它(握手已锁,见 `03` §2) | ✅ |
| 13 | face-player-single | `S` | 设自机表情(face) | case 0xd:interrupt_and_run(face 0x40, arg+0x11) | ✅ |
| 14 | face-enemy | `SS` | 设某敌方表情(who, face) | case 0xe → `interrupt_and_run(+0x44[arg], face+0x11)` | ✅ |
| 15 | text-1 | `m` | 设第一行文本(**unused**) | case 0xf:取串→喂文本行1 anm(0x58) | ✅ |
| 16 | text-2 | `m` | 设第二行文本(**unused**) | case 0x10:取串→文本行2 anm(0x5c) | ✅ |
| 17 | **text-add** | `m` | **追加下一行文本**(主用文本指令) | case 0x11:主文本路径(串+注音+`\|x,y,` 定位语法) | ✅ |
| 18 | text-clear | — | 隐藏全部文本 | case 0x12:unload 0x6c + interrupt 文本/注音槽 | ✅ |
| 19 | music-boss | — | 起 boss 音乐 + 显示曲名 | case 0x13:`FUN_0043c3f0(1,…)` + GUI 特效 anm | ✅ |
| 20 | intro | `S` | 显示某敌人名字 + flavor text(who) | case 0x14:按 stage 表建 intro anm(+0x48)→ FUN_0042c480 | ✅ |
| 21 | stage-end | — | 结算关卡奖励、进下一关 | case 0x15 → `FUN_0042e150()` | ✅ |
| 22 | **music-fade** | — | 关卡末淡出音乐 | case 0x16 → `FUN_0043c470`(BGM 调整)**〔纠正:原 doc 误把 shake 标在 22〕** | ✅盲验证 |
| 23 | **shake-player-single** | — | 自机立绘短暂抖动(如 Nitori) | case 0x17:`interrupt_tree(+0x40, 7)` 自机立绘 | ✅盲验证 |
| 24 | **shake-enemy** | — | 敌方立绘短暂抖动 | case 0x18:`interrupt_tree(+0x44/+0x48, 7)` | ✅盲验证 |
| 25 | y-offset | `S` | **给所有文本加垂直偏移 dy** | case 0x19:写立绘 `+0x4e4 = (float)arg`(=y 偏移,纠正 01 的"alpha?"猜测) | ✅ |
| 26 | modern-26 | — | 置某调字体的位 | case 0x1a:`flags \|= 2` | ✅ |
| 27 | music-fade-custom | `f` | 按自定义时长淡出音乐 | case 0x1b → `FUN_0043c470`(同 22 的 BGM 函数);⚠️ 盲读未见读 float 实参,与 ExpHP `f` 签名有出入 | 🟡 |
| 28 | **callout-pos** | `ff` | **设气泡(speech bubble)位置 x,y** | case 0x1c:写 `+0x1b0/+0x1b4`(两 float ×2) | ✅✅ |
| 29 | callout-type | `S` | 设气泡类型 | case 0x1d:`flags ^= (arg<<2 ^ flags)&0x3c` | ✅ |
| 30 | 128-route-select | — | (TH128 残留)分路选择 | (case 缺;TH16 未用) | 🟡 |
| 31 | show-enemy-1 | `S` | 等价 show-enemy(1) | case 0x1f:建敌方立绘槽 +0x48 | ✅ |
| 32 | **modern-32** | `S` | **设说话方 side,但不改高亮立绘** | case 0x20:`active_side = arg` | ✅ |
| 33 | **darken-portrait** | `SS` | 变暗单个立绘(不改 active speaker)(side, who) | case 0x21:`interrupt_and_run(+0x44[instr+8], 3)`(读两参) | ✅ |
| 34 | **highlight-portrait** | `SS` | 高亮单个立绘如同在说话(不改 active)(side, who) | case 0x22:同上 param 2 | ✅ |
| 35 | **lights-out** | — | 用黑色盖住关卡背景与敌人 | case 0x23 → `FUN_00426780()` | ✅ |

## 3. 编号对齐注(TH11 插位 + TH14 override,易错)

- **TH11 在 ins 9 处插了 `focus-none`**,使 TH10 的 9..23 全体 +1。所以 TH10 的 `text`(14/15/16)在 TH16 变成
  **15/16/17**,`pause`(TH10 ins10)变 **11**,等等。**别拿 TH10 的编号套 TH16。**
- **TH14 override**:5→hide-enemy、8→focus-enemy、14→face-enemy、20→intro、24→shake-enemy(把 TH10/11 的
  "-single"无参版换成带 who/side 参数版),并加 32 modern-32。
- 我们 exe 的 case 编号(0x.. = 十进制)与本表 opcode **直接相等**(`run` 的 switch 就是 `switch(instr->opcode)`,
  **无二级跳表重映射**,区别于 ECL 的 `ecl_run_over_300`)。
- ✅ **22/23/24 已盲验证对齐**(2026-06-11 独立子 agent 不喂标签盲读):exe case=opcode 恒等;**22=case0x16(BGM,music-fade)、
  23=case0x17(interrupt7 自机=shake-player)、24=case0x18(interrupt7 槽=shake-enemy)**。修正了本 doc 初稿把 shake 错放到 22 并漏掉
  music-fade 的转录错——校正后 ExpHP 名与 exe case 全部吻合。

## 3.5 独立盲验证(2026-06-11)

派**未喂任何我们/ExpHP 命名**的子 agent 重反 `GuiMsgVm::run`(0x42A1D0),用中立机械描述逐 case 复核(防过拟合,
memory `re-agent-no-hypothesis-priming`)。结果:**绝大多数 ✅ 印证**(0/1/2/4/5/6/10/11/12/13/14/15/16/17/18/19/20/21/25/26/28/29/31/32/33/34/35
行为与本表一致,且独立确认 12=ecl-resume 写 +0x18c、25=y-offset 写 +0x4e4、28=两 float、33/34 读 +4 与 +8 两参)。
**纠错**:22/23/24 对齐(见上)。**澄清**:op3、op0x1e(30)在 `run` 中**无 case**(nop/未用)。

## 4. 与 ECL 的握手(闭环)

`01` 已立:ECL `ins 518 dialogRead(对话id)` 起对话、`ins 519 dialogWait` 阻塞敌机脚本。本表补上**对话侧的释放点**:
**MSG `ins 12 ecl-resume`** 唤醒在等 MSG 的 ECL(ExpHP:"used to tell the boss when to fly")——即对话脚本里
用 ins 12 通知 ECL"对话演到此处,boss 可以动了"。三者构成完整协程式握手:
```
ECL:  518 dialogRead(id) ───► 起 GuiMsgVm
ECL:  519 dialogWait ────────► 卡住,等
MSG:  …演出… 12 ecl-resume ──► 放行上面的 519
MSG:  0 end ────────────────► 拆 VM(on_tick_20 检 run==-1)
```
✅ **握手已逐指令锁定**(`ins 12` 写 `vm[0x18c]` 一帧脉冲、`519 dialogWait`@0x4216e0 读它、run 顶部每帧清)——详见 `03-dialogue-lifecycle.md` §2。

## 5. 下一步

1. **对死 🟡 项**(12 ecl-resume 的 +0x18c 信号链、22/23/24 shake、3/27/30)——逐条反编译 `run` 对应 case + 找
   `519 dialogWait`(0x4216e0)的检查点,把握手字段彻底锁死 → `03-dialogue-lifecycle.md`。
2. **`\|x,y,` 文本定位语法**(ins 17 内 `FUN_0042bbe0`/`FUN_00476c60`)精解——对 thcrap 译文 / IDE 文本编辑相关。
3. **结局/staff 第二指令集**(独立,优先级低)。
4. **回填 `../../docs/`**:IDE 的 MSG 支持 = 本表(结构化 opcode 编辑)+ §1 文本编解码 + thmsg/truth 互通。

## 证据指针

- 一手:`GuiMsgVm::run` 0x42A1D0(switch on `instr->opcode`,case 0..0x23);`Gui::start_dialogue` 0x429FF0;
  ECL `dialogRead/Wait` 0x4216b3/0x4216e0。
- ExpHP truth:`map`/`src/core_mapfiles/msg.rs`(MSG_10_185,签名+逐版本编号);GitHub `ExpHP/truth`。
- ExpHP thpages:`js/tables/reference/msg.ts`(名+行为 prose);站点 <https://exphp.github.io/thpages/>(MSG 页;**注:为 stage MSG**)。
- 社区来源速查见 `../shared/touhou-modding-sources.md`。
