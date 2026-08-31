# ecl — ECL 敌机/弹幕脚本 VM

**没有全局 VM。每个敌机自带一个解释器**，各自持有调用栈和变量，主循环逐个 tick。
opcode 分两层：**系统 opcode**（0–0x5d，控制流/变量/栈，VM 自己实现）与**游戏 opcode**
（300+，创建敌机、发弹、移动，转调引擎函数）。这两层的分界就是 modding 的主要接缝。

文件格式（`.ecl` 二进制、thecl 的降级规则、eclmap 命名层）见
[`format-reference.md`](format-reference.md)——那部分跨版本，不放在版本目录下。

## 断言 × 版本矩阵

| 断言 | th16 | th18 | 证据 |
| --- | :---: | :---: | --- |
| 每敌机一个解释器，无全局 VM | ✅ | 🟡 | [th16/02 §1](th16/02-runtime-vm.md)、[th16/07 §2](th16/07-vm-architecture.md) |
| 取指-解码-执行主循环 = `EclRunContext::ecl_run` @0x472030 | ✅ | 🟡 | [th16/04 §2](th16/04-ecl-vm-interpreter.md)、[th16/07 §3](th16/07-vm-architecture.md) |
| opcode 两层：系统 0–0x5d + 游戏 300+ | ✅ | 🟡 | [th16/04 §3](th16/04-ecl-vm-interpreter.md)、[th16/05 §1](th16/05-fire-interface.md) |
| `0x4921ac..` 是**变量访问器表**，不是 opcode 派发表（易错） | ✅ | 🟡 | [th16/01 §1](th16/01-ecl-context-and-variables.md) |
| **无未公开游戏 opcode**（负结论，对照 Priw8 eclmap 穷尽） | ✅ | 🟡 | [th16/05 §2](th16/05-fire-interface.md) |
| 开火接缝 = 发射器结构体充当 fire 描述符（双向自洽） | ✅ | 🟡 | [th16/05 §3](th16/05-fire-interface.md) |
| `ecl_enm_create` @0x423050 承载 op 300/301/304/305/309/311/312/321 | ✅ | 🟡 | [th16/05 §4](th16/05-fire-interface.md) |
| 可用「范围闸」patch 加自定义指令，不必动跳转表 | 🟡 | — | [th16/06](th16/06-adding-custom-instructions.md)（从 ECLplus 的 TH17 做法映射，未实跑） |

> **图例**：✅ 该版本一手验过（证据列给地址/出处） · 🟡 待验（从别的版本借来的假设，或单源） · ❌ 已知不同/不存在 · ❓ 存疑 · — 未看
>
> **本页不许出现没有出处的断言。** 从某作借到另一作的判断一律 🟡，在该版本 exe 上验过才能改 ✅（[`METHOD.md`](../../METHOD.md)）。

## 开放

- 「范围闸」配方**尚未在游戏里跑过**，标 🟡；要落地走 [`../../mods/`](../../mods/README.md) 的流程。
- 帧末浮点插值器 `float_i[8]` 的完整语义仍有边角未清（[th16/04 §5](th16/04-ecl-vm-interpreter.md)）。
- 与 ExpHP th-re-data 的命名差异与 2 处真冲突裁决记录在 [th16/03](th16/03-thredata-crosscheck.md)。
