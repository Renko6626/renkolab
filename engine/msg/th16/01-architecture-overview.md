# 01 · TH16 MSG(对话/文本)系统 —— 整体架构与编排

> 适用:**TH16《鬼形兽》`th16.exe` v1.00a**(imagebase 0x400000)。勿外推到其它作。
> 本篇只画**整体结构 / 工作流 / 子系统边界 / 编排关系**,不逐 opcode 展开(opcode 表见将来 `02-*`)。
> 证据等级:**✅ 一手反编译+多源交叉** / 🟡 单源或部分 / ❓ 待查。方法见 `../sht/findings/00-METHOD-*`。
>
> **三方交叉已对上**(这是本篇可信度高的原因):一手反编译(Ghidra `th16` DB)× ExpHP th-re-data
> 命名/结构体 × thtk eclmap `th16.eclm`。凡三者一致处标 ✅。

---

## 0. 一句话结论

TH16 的"对话/文本"**不是单一 VM,而是一个格式(`.msg`)被两套场景消费**:
1. **关卡内对话**——`GuiMsgVm`,由 `Gui` 每帧驱动,**由 ECL 脚本 ins 518/519 触发并握手**。← 本篇主线,已基本反完编排。
2. **结局 + Staff Roll**——`Ending` 场景独立消费 `e0X.msg` / `staffX.msg`,**另一套解释器**(未反)。← 第二子系统,仅定位。

`.msg` 是**外部文件**(打在 THA1 归档里),运行时读进内存缓冲再由 VM 解释。文本最终**走 ANM 渲染**(不是 GDI `draw_text`——纠正了 README 起步锚点 B 的猜测)。

---

## 1. 子系统地图(谁是谁)

| 子系统 | 地址 | 角色 | 证据 |
| --- | --- | --- | --- |
| **`Gui`**(单例 `GUI_PTR`) | ctor 0x4268C0 / init 0x426B00 | 关卡内 HUD + 对话宿主;持有 msg 文件缓冲(+0x1cc)与活动 VM 指针(+0x1c8) | ✅ |
| `Gui::sub_426c10` | 0x426C10 | **`.msg` 文件加载器** → 写 `Gui+0x1cc` | ✅ |
| `Gui::start_dialogue` | 0x429FF0 | **对话触发多路器**(ECL 调用入口) | ✅ th-re-data 命名 |
| `Gui::on_tick_20` | 0x427CF0 | **每帧驱动**(UpdateFunc 优先级 0x20):跑 VM + 完成后拆 | ✅ |
| `Gui::on_draw_2` | 0x428E70 | 对话层绘制(优先级 0x33/0x30) | 🟡 命名,未细看 |
| **`GuiMsgVm`**(struct `zGuiMsgVm`,0x1c8 字节) | — | **关卡内对话脚本 VM** 本体 | ✅ th-re-data struct |
| `GuiMsgVm::initialize` | 0x429B20 | 绑定脚本起点、建 ANM 立绘/文本槽 | ✅ |
| `GuiMsgVm::run` | 0x42A1D0 | **取指-派发主循环**(opcode 0..0x23) | ✅ |
| `GuiMsgVm::destructor` | 0x4264A0 | 拆 VM(回收 ANM 槽) | ✅ |
| `EnemyData::ecl_run_over_300` | 0x41DD51 | ECL 高位指令派发器;ins **518/519** 在此 | ✅ |
| **`Ending`** 场景 | init 0x4191F0 / tick 0x4199F0 | **结局 + staff roll** 消费 `e0X.msg`/`staffX.msg`(独立) | 🟡 仅定位 |

---

## 2. 数据/控制流(关卡内对话,主线)—— 全链路 ✅

```
                    [stage 装载期]
CUR_TABLE_STAGE_FILES +0x14+(subshot+character)*4  ← 按角色选 .msg 文件名(stXXy.msg)
        │
        ▼  Gui::sub_426c10 (0x426C10)  ← 由 Gui::initialize / GameThread 调
   reads_file_into_new_allocation_402440(THA1 归档读)  →  malloc 缓冲
        │
        ▼  存入  Gui+0x1cc   (msg 文件缓冲;退场由 FUN_00427970 free)
        ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄
                    [关卡运行期 · ECL 脚本驱动]
   ECL 敌机脚本执行  ins 518 dialogRead(S=对话id)   ← EnemyData::ecl_run_over_300 case 0x3f
        │
        ▼  Gui::start_dialogue(GUI_PTR, id)   +  清空全部子弹/敌人(BulletManager::clear_all + et_clear_all_special)
        │     id>=0 : operator_new(0x1c8) → GuiMsgVm::initialize(vm, Gui+0x1cc 里第 id 条脚本)
        │             vm 存入 Gui+0x1c8 ; vm[0]=id
        │     id=-1/-3 : 不建 VM → 放 boss 登场语音(.wav)+ 换 BGM
        │     id=-2 : 符卡相关分支
        ▼
   每帧 Gui::on_tick_20:  if (Gui+0x1c8 != 0)  ret = GuiMsgVm::run(vm)
        │                     ret==0          → 继续(推进计时/速度倍率)
        │                     ret==0xffffffff → GuiMsgVm::destructor + free + Gui+0x1c8=0
        │
        ▼  GuiMsgVm::run 逐条解释 opcode → 文本/立绘喂给 AnmManager VM(FUN_0046d990 文本转 anm)
        ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄
   ECL 侧  ins 519 dialogWait  ← 阻塞敌机脚本,直到 Gui+0x1c8 对话结束才放行
```

**ECL↔MSG 握手**(用户关心的"对话被 ECL 触发"):敌机 ECL 脚本里成对出现
`518 dialogRead(id)` 起对话 → `519 dialogWait` 卡住后续脚本直到对话播完。两条都在
`EnemyData::ecl_run_over_300`(0x41DD51,高位指令派发器,字节索引跳表 @0x422c44)。
- 证据:th-re-data `labels.json` 标 `0x4216b3 = 518__dialogRead`、`0x4216e0 = 519__dialogWait`;
  eclmap `th16.eclm` 签名 `518 S`(一个 int 实参 = 对话 id);一手反编译 case 0x3f 调 `Gui::start_dialogue`
  且 `byte_table[518-300]=0x3f`(同表 300/304→case0=enmCreate 自洽对齐)。**三方一致 ✅**。

**对话期的全局门控**:`Gui+0x1c8 != 0`(对话活跃)被当全局闸用——boss 计时块、敌人血条/季节槽 UI
在对话期被**抑制**(on_tick_20 内两处条件)。即对话独占画面、暂停关卡推进。✅

---

## 3. 文件格式 ↔ 运行时结构(对 thmsg 的锚)

**指令 `zMsgRawInstr`(8 字节头 + 变长实参)** — th-re-data struct,与 `run` 推进步长一手吻合:
```
0x0  int16  time        每条指令的触发帧(相对脚本起点)
0x2  uint8  opcode       指令号(run 里 switch 的就是它,0..0x23)
0x3  uint8  args_size    实参字节数  → run 末尾 current_instr += args_size + 4 推进
0x4  args[]              按 opcode 解释(thmsg 给布局)
```
- 一手证据:`GuiMsgVm::run` 末尾 `*(p+0x158) += *(byte*)(*(p+0x158)+3) + 4`(读 +3=args_size,跳过 4 字节头)。
- **文件头** = 8 字节一条的入口表:`start_dialogue` 取 `*(Gui+0x1cc + 4 + id*8) + (Gui+0x1cc)` 当第 id 段脚本起点
  → 头部每条 8 字节,+4 处是该对话脚本的偏移。🟡(偏移语义一手,入口表项其余字段未验)。
- 交叉锚:**thmsg(thtk)对 TH16 的 stgmsg ins_ 表** = 权威格式侧;逐 opcode 对照留给 `02-*`。

**VM 状态 `zGuiMsgVm`(0x1c8 字节)** 关键字段(th-re-data,部分一手印证):
| off | 字段 | 含义 |
| --- | --- | --- |
| 0x0 | (id) | 当前对话 id(start_dialogue 写入) |
| 0x18/0x2c | time_in_script / pause_timer | 脚本计时 / 等待计时(zTimer) |
| 0x40 | anm_id_player_face | 自机立绘 ANM id |
| 0x44 | anm_id_enemy_face[4] | 敌方立绘 ANM id(4 个) |
| 0x58/0x5c | anm_id_text_line_1/2 | 文本两行 ANM id |
| 0x60/0x64 | anm_id_furigana_1/2 | 注音(furigana)ANM id |
| 0x158 | current_instr | **指令指针**(zMsgRawInstr*),取指就读它 |
| 0x190 | flags | 运行标志位(opcode 0x1a/0x1d 改) |
| 0x194 | next_text_line | 下一文本行状态 |
| 0x19c | active_side | 说话方(0=左/自机侧, 1=右/敌方侧;opcode 7/8 切) |
| 0x1ac | callout_pos | 气泡/呼出位置 |

**渲染端**:文本/立绘**不走 GDI**,而是 `GuiMsgVm::run` 把字符串/坐标喂给 `AnmManager` 的 ANM VM
(`FUN_0046d990` = 文本转 anm)。立绘、文本行、注音都是独立 ANM 子树。→ 纠正 README 锚点 B(draw_text/0x459240
是别处的 GDI 文本,**非** MSG 主路径)。✅(run 内一手:全程 AnmLoaded__create_effect / AnmManager__interrupt_tree)。

---

## 4. opcode 表(GuiMsgVm::run,0..0x23)—— 🟡 初步骨架,待 `02-*` 对 thmsg 精解

> 仅"扫一遍 switch"得的粗语义,**未逐个反编译验证、未对 thmsg 命名**,一律 🟡。下一步主攻。

| opcode | 粗看行为(🟡) |
| --- | --- |
| 0 | **结束**(`return -1` → 触发拆 VM) |
| 1 | 显示自机/敌方立绘(create_effect) |
| 2 | 显示某敌方立绘(按 stage 文件表索引) |
| 4/5/6 | 隐藏/中断立绘(自机/敌方/全部) |
| 7/8 | 布局到 左侧/右侧(写 active_side 0/1) |
| 9 | 立绘进场动画(带位移) |
| 0xb | **等待输入**(pause_timer + 射击/Bomb 键推进;13 帧节流) |
| 0xc | 停一帧 |
| 0xd/0xe | 立绘播放某段(interrupt_tree_and_run) |
| 0xf/0x10/0x11 | **渲染文本行**(行1/行2/主路径;走 anm,带 `|x,y,` 定位语法解析) |
| 0x12 | 清文本/收起文本框 |
| 0x13/0x14 | 关卡特效 / boss 登场 anm |
| 0x15/0x16/0x1b | 调 GameThread/stage 推进相关(FUN_0042e150/43c470) |
| 0x17/0x18 | 中断立绘树(7=??) |
| 0x19 | 给立绘写 +0x4e4(某参数/alpha?) |
| 0x1a | flags |= 2 |
| 0x1c | 写 callout_pos(0x1b0/0x1b4,值×2) |
| 0x1d | flags 改 bits(<<2 & 0x3c) |
| 0x1f | 另一敌方立绘槽(+0x48) |
| 0x20 | 设 active_side = 实参 |
| 0x21/0x22 | 立绘 interrupt_and_run(参 3/2) |
| 0x23 | 调 FUN_00426780 |

⚠️ 这张表**必过四闸门复核**(逐个反编译 + 对 thmsg ins 名 + 真 .msg 取值)才能升 ✅。现状仅供 `02-*` 起步。

---

## 5. 第二子系统:结局 / Staff Roll(独立,未反)🟡

- `e01.msg`..`e08.msg`(8 个结局)在文件名表 @0x491780;`staff1..4.msg` 在 @0x4917A0,
  且 **`Ending::on_tick_23__main`(0x4199F0)直接引用 `staff1.msg`(0x419F0D)** → 结局场景自己消费。
- 即结局/staff 文本**不经 GuiMsgVm**,是 `Ending` 场景(`Ending::initialize` 0x4191F0 / `on_tick_23` 0x4196C0)
  的独立解释器。**格式同为 `.msg`**(thmsg 的 endmsg 变体),但运行时是另一套 VM。
- 状态:仅定位,未反编译。列为 MSG 系统的**第二条线**,优先级低于关卡内对话。

---

## 6. 开放问题 / 下一步

1. **opcode 表精解(主攻)**:逐个反编译 `GuiMsgVm::run` 的 0..0x23,对 thmsg `th16` stgmsg ins_ 表命名,
   产出"opcode→行为"权威表 → `02-msg-vm-opcodes.md`。⚠️ 防过拟合:派子 agent 给中立判据、不喂 thmsg 标签。
2. **文件头/入口表布局**:验 `Gui+0x1cc` 头部 8 字节项的其余字段(只确认了 +4=偏移)。
3. **文本定位语法**:opcode 0x11 里 `|x,y,文本` 的解析(FUN_0042bbe0 取串、FUN_00476c60 切逗号)——对 thcrap 译文有用。
4. **结局/staff 第二 VM**:`Ending::on_tick_23__main` 怎么解 `e0X.msg`/`staffX.msg`(独立优先级低)。
5. **回填**:稳定后 → `../../docs/`(IDE 的 MSG 支持:结构化 opcode 编辑 + 对 thmsg)。

## 证据指针(便于复核)

th16.exe v1.00a:`Gui::start_dialogue` 0x429FF0、`Gui::sub_426c10` 0x426C10、`Gui::on_tick_20` 0x427CF0、
`GuiMsgVm::run` 0x42A1D0、`GuiMsgVm::initialize` 0x429B20、`EnemyData::ecl_run_over_300` 0x41DD51
(ins 518 调用点 0x4216C3,跳表 @0x422C44)、归档读 0x402440、文本转 anm 0x46D990、
`Ending::on_tick_23__main` 0x4199F0。
th-re-data:`data/th16.v1.00a/{funcs,labels,type-structs-own}.json`(GuiMsgVm/zMsgRawInstr/zGuiMsgVm)。
eclmap:`research/ecl/vendor/th16.eclm`(`518 S` / `519`)。
