# msg — MSG 对话/文本系统

`.msg` 是一个容器，但**有两套互不相干的消费者**：关卡内对话（`GuiMsgVm`）和结局/staff roll（`Ending`）。
两者**各有一套 opcode**，编号重叠但含义不同——这是读 MSG 最容易踩的坑。

关卡对话与 ECL 之间是**协程式握手**：ECL 用 ins 518/519 把控制权交给 MSG VM，等它跑完再收回。
文本的实际绘制走 ANM 精灵，不是 GDI——所以「换字体/排版」的接缝在 ANM 那边，不在 MSG。

## 断言 × 版本矩阵

| 断言 | th16 | th19/th20 | 证据 |
| --- | :---: | :---: | --- |
| `.msg` 有两套独立指令集：关卡对话 vs 结局/staff | ✅ | 🟡 | [th16/01 §1,§5](th16/01-architecture-overview.md)、[th16/04 §2](th16/04-ending-staff-msg-instruction-set.md) |
| 关卡对话由 `GuiMsgVm::run` 驱动，opcode 0..0x23 | ✅ | 🟡 | [th16/01 §4](th16/01-architecture-overview.md)、[th16/02 §2](th16/02-msg-vm-opcodes.md) |
| ECL ins **518/519** 与 MSG 协程握手（逐指令锁定） | ✅ | 🟡 | [th16/03 §2](th16/03-dialogue-lifecycle.md) |
| 文本绘制走 **ANM 精灵**，非 GDI | ✅ | 🟡 | [th16/01 §2](th16/01-architecture-overview.md) |
| 结局/staff 指令集与关卡对话**编号重叠但语义不同** | ✅ | 🟡 | [th16/04 §2](th16/04-ending-staff-msg-instruction-set.md) |
| 指令集有 TH11 插位 + TH14 override 的继承链（跨版本对号易错） | ✅ | 🟡 | [th16/02 §0,§3](th16/02-msg-vm-opcodes.md) |

> **图例**：✅ 该版本一手验过（证据列给地址/出处） · 🟡 待验（从别的版本借来的假设，或单源） · ❌ 已知不同/不存在 · ❓ 存疑 · — 未看
>
> **本页不许出现没有出处的断言。** 从某作借到另一作的判断一律 🟡，在该版本 exe 上验过才能改 ✅（[`METHOD.md`](../../METHOD.md)）。

## 与 thmsg / THTK-Studio 的关系

TH16 的两张 opcode 表已经过 thmsg 交叉验证与真实数据（`e01.msg` / `staff1-4.msg`）验证。
下一步若要给 **th19/th20** 补指令名，方法照搬：在 Ghidra 里定位该版本的 `GuiMsgVm::run`，
对照 opcode 分支的行为命名，每确认一条就往 eclmap/msgm 加一行。

## 开放

- 结局表里 op4 / 0xd / 0xf-0x11 **未在真实数据中现身**，可信度来源较弱（[th16/04 §2.7](th16/04-ending-staff-msg-instruction-set.md)）。
- 「这是不是第一张 ending opcode 表」的诚实校准见 [th16/04 §2.6](th16/04-ending-staff-msg-instruction-set.md)——别过拟合。
