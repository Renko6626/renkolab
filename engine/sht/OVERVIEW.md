# sht — SHT 自机（shoot type）配置

**SHT 不是脚本语言，是纯二进制配置文件**，逐版本差异大。它描述一个自机的移动速度、判定、
以及一组组 shooter（发弹器）；运行时按「火力档 × 聚焦」选中一组，逐个 shooter 派发。

难点从来不是字节布局（社区早已搞清），而是 **`func_on_init/tick/draw/hit` 这些行为函数索引到底指向什么**，
以及 `flags` 段的含义——社区至今无公开破解。**TH16 这块已经攻下**：四张跳转表全反、
索引→行为表建立、`flags` 证明为运行时不读。

格式与工具现状见 [`format-reference.md`](format-reference.md) 与 [`tools-analysis.md`](tools-analysis.md)（跨版本）。

## 断言 × 版本矩阵

| 断言 | th16 | th18 | 证据 |
| --- | :---: | :---: | --- |
| SHT 是纯二进制配置，无脚本语义（→ IDE 该做表单而非编译） | ✅ | ✅ | [format-reference.md](format-reference.md)、[th16/01](th16/01-runtime-semantics.md) |
| 解析器 `sht_parse_resolve_funcptrs` @0x443790 把 func_\* 索引**解成函数指针**，无边界检查 | ✅ | 🟡 | [th16/03 §1](th16/03-th16-funcstar-jumptables.md) |
| 四张函数指针表在 .rdata（tick 表 @0x4919a0） | ✅ | 🟡 | [th16/03 §2](th16/03-th16-funcstar-jumptables.md)、[th16/04 §3](th16/04-th16-shot-runtime-architecture.md) |
| shooter 结构 stride = **0x58** | ✅ | ✅ | [th16/05 §2](th16/05-th16-flags-no-runtime-read.md)；th18 由 ExpHP `zShtShooter` 佐证 |
| **`flags` 段运行时完全不被读**（负结论，过了对抗证伪） | ✅ | 🟡 | [th16/05 §3–4](th16/05-th16-flags-no-runtime-read.md) |
| shooterset 按「火力档 × 聚焦」选择，`Player__do_shooting` @0x445470 | ✅ | 🟡 | [th16/07 §1](th16/07-th16-shooterset-organization.md) |
| 组内区分主弹与子机弹 | ✅ | 🟡 | [th16/07 §2](th16/07-th16-shooterset-organization.md) |
| 自机弹伤害管线：伤害源池 `PLAYER+0xd080`，stride 0x94，256 个 | ✅ | 🟡 | [th16/08 §1–2](th16/08-th16-player-damage-pipeline.md) |
| header `+0x04`「可配置判定半径」是**哑弹**——运行时不读 | ✅ | 🟡 | [th16/99-QUIRK](th16/99-QUIRK-可配置判定半径其实是哑弹.md) |

> **图例**：✅ 该版本一手验过（证据列给地址/出处） · 🟡 待验（从别的版本借来的假设，或单源） · ❌ 已知不同/不存在 · ❓ 存疑 · — 未看
>
> **本页不许出现没有出处的断言。** 从某作借到另一作的判断一律 🟡，在该版本 exe 上验过才能改 ✅（[`METHOD.md`](../../METHOD.md)）。

## ⚠️ 这个子系统的宣称风险最高

上表多条是**社区标 `unknown` 而我们解开的**，没有外部佐证 = 风险最高。
每条都过了 [`METHOD.md`](../../METHOD.md) 的四道闸门（一手到底 / 对抗证伪 / 量纲常识 / 交叉对名），
踩过的坑记录在 [th16/99-QUIRK](th16/99-QUIRK-可配置判定半径其实是哑弹.md) 和
[th16/02](th16/02-community-recheck-funcstar-flags.md)。**动它们之前先读那两篇。**

## 开放

- TH18/TH19 完全未验：func_\* 编号是否与 TH16 共用、`flags` 是否到新作才启用，都需要样本。
- 引擎其余切口（敌人/道具/图形/音效）的锚点索引见 [th16/06](th16/06-th16-engine-incisions.md)。
