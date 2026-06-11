# research/msg/ — TH16 MSG(对话/文本)系统逆向(新会话入口)

> 本文件夹专做一件事:**逆向 TH16《鬼形兽》(`th16.exe`,imagebase `0x400000`)的 MSG 系统**——
> 即 `.msg` 里的**对话/文本脚本 VM** 与运行时:关卡前后对话、立绘/说话人、逐行文本、等待输入、
> 表情/语音/音效、结局文本等。东方的"剧情/对话"层就挂在 MSG 上。
> 你若是**新 Claude 会话**,读完这份 README 应知道目标、规范、环境、和**从哪一刀切**。
>
> ⚠️ **现状**:本文件夹**尚未系统开工**(与 `../anm/` 同为占位入口)。下面的"起步锚点"是别处顺到的口子,
> 多为 🟡(子系统名/二手),**动手时务必自己反编译复核**,别当定论。
> **为什么值得做**:MSG 是 IDE 的目标格式之一(ECL/ANM/**MSG**/STD),且对话系统运行时**我们一点没碰**——
> 空间大、自包含,格式侧有 thmsg 权威可交叉印证。

## 目标

1. **MSG VM 主体**:谁每帧/每步驱动对话脚本?opcode 表(设说话人/立绘/逐行文本/等待/表情/语音/淡入淡出/结束)→ 行为。
2. **对话生命周期**:对话怎么被触发(关卡脚本/ECL?)、与暂停/输入的交互、结束后还控制权给谁。
3. **格式 ↔ 运行时**:把运行时 opcode 与 `thmsg.exe`(thtk)反汇编出的 MSG 指令号/语义对应,产出"指令号→行为"表。
4. **文本/编码**:MSG 文本编码(Shift-JIS / UTF-8 经 thcrap)、与字体渲染(`draw_text` 0x459240,见下)的接缝。
5. 回填父仓库 `../../docs/`(将来 IDE 的 MSG 支持)。

## 规范(与父工作区一致)

- **五段证据链**(发现→推测→验证→结论(可信度+版本)→证据(地址/出处)):`../sht/findings/00-METHOD-逆向记录纪律.md`。
- **可信度** ✅一手实证 / 🟡单源或推断 / ❓存疑;**结论必注版本(仅 TH16,勿外推)**。
- **防过拟合**:派子 agent 命名给中立判据、不喂标签;"反超社区"自创结论按四闸门复核;验证前往下取整标 🟡。
  (memory `re-overclaim-guard` / `re-agent-no-hypothesis-priming` / `re-evidence-chain-discipline` / `re-workflow-fanout-cost`)
- **主仓库不留版权字节**:游戏 exe / .msg 资产 / 大段反编译原文一律 gitignore;只提交脚本 + markdown。

## 环境(已就绪,与父工作区共用)

- **ghidra-re MCP**,database `th16`(已分析,含 SHT/数学/弹幕/ECL/归档模块命名)。MCP `rename_function`/`rename_address`/
  `set_comment`/类型 + `save_database` 跨会话可靠落盘(★每批必显式 save);隐藏工具走 `batch`/`call`,目录见 `../shared/ghidra-mcp-tools.md`。
- 常量/字节直读:MCP `read_bytes`,或解析 PE `../files/th16.exe`。
- **★★ 逆向先翻 `../ecl/vendor/th-re-data`**(ExpHP,gitignored)= TH16 符号金矿,**很可能已命名 MsgVm/GuiMsgVm
  相关函数 + 结构体**;`../funcs/import_th_re_data.py` 一键套进 Ghidra(当前 th16 工程已套用)。详见 `../shared/touhou-modding-sources.md`。
- 落盘:命名脚本 `../sht/disasm/scripts/apply_th16_msg_names.py`(建议,待建);文档 → 本文件夹。

## 起步锚点(starting points,🟡 待一手复核)

### A. ★ in-exe 入口:`GuiMsgVm` 子系统
- `funcs/unexplored.md` 聚合显示 **`GuiMsgVm` 子系统有 ~8 个未命名函数**(nearest-named 邻居)——很可能就是 MSG 对话 VM
  的执行/派发/渲染。**第一刀**:在 th16 DB 里 `list_functions filter "(?i)guimsg|msg"` 找 ExpHP/我们已命名的锚点,
  顺其 xref 找对话 VM 的取指-派发循环(类比 ECL 的 `ecl_run`)。
- ⚠️ `GuiMsgVm` 这个名是 nearest-named 提示,**别假定那 8 个都是 MSG**(参 Arcfile 的 `0x458730` 教训:hint 会误导)。

### B. 文本渲染接缝:`draw_text`(0x459240)
- 反归档时旁证到:**`draw_text` @0x459240** 用 GDI(`TextOutA`)在表面 `DAT_004a5d80` 上渲文本,再 `D3DXLoadSurfaceFromMemory`
  上 D3D(`0x458730` 是其字形平滑 pass,见 `../shared/th16-archive-thai-lzss.md` §4)。MSG 逐行文本最终大概率走这条。
  **可作"文本输出端"锚点**,反推谁(MSG VM)在喂它字符串。

### C. 与符卡名/MSG 的已知事实
- ✅ **符卡名属 MSG,不是 SHT**(见 `../shared/touhou-modding-sources.md`)。我们在 SHT/scorefile 侧碰过符卡记录
  (`../sht/findings/05`),但符卡**名字**的文本在 MSG/对应资源——做 MSG 时可对上。

## 社区对照(关键:有 thmsg 可交叉印证)

- **`thmsg.exe`**(thtk,`thpatch/thtk`):MSG 的反汇编/重编译工具,**有完整 opcode 表与格式定义**(C 源)。
  把"运行时 opcode"对到"格式指令号"的**权威外部锚点**——逆向时**先看 thmsg 的 ins_ 表**,再去 exe 核对实现。
- **thcrap**:MSG 是翻译补丁的主要目标(对话译文),社区对 MSG 指令/文本流理解充分;Priw8/thpatch 文档可查。
- **ExpHP `th-re-data`**:符号/结构体金矿(见环境)。⚠️ 它给"叫什么/字段在哪",不给"干什么"——语义自己做。
- 速查 `../shared/touhou-modding-sources.md`;参考仓库克隆走 `vendor/`(gitignore)。
- ⚠️ thmsg 给**格式**语义;**运行时**实现(VM 怎么解释、文本怎么排版/分页/等待)仍须在 th16.exe 自证;TH16 是新作,以 thmsg 对 TH16 支持为准。

## 计划产出

- `01-msg-vm-opcodes.md`(对话 VM + opcode 表,对 thmsg)、`02-dialogue-lifecycle.md`(触发/输入/渲染接缝)。
- `../sht/disasm/scripts/apply_th16_msg_names.py`(函数/数据符号/注释,headless 可复现)。
- 稳定后回填 `../../docs/`。

## 关联

- 文本渲染端:`../shared/th16-archive-thai-lzss.md` §4(draw_text/0x458730 字形平滑);未来 `../anm/`(若文本走 anm 显示)。
- VM 范式参考:`../ecl/07-vm-architecture.md`(ECL 的"取指-门控-派发"模型,MSG VM 可类比)。
- 主循环:`../shared/th16-main-loop.md`(对话阶段挂在哪个 on_tick)。
- 纪律:`../sht/findings/00-METHOD-逆向记录纪律.md`;memory `re-overclaim-guard` 等。
