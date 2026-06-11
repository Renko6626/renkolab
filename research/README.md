# research/ — 研究工作区(新会话先读这里)

本目录是 THTK-Studio 动手写代码之前的**研究/逆向工作区**。如果你是一个**新的 Claude 会话**、
没有之前对话的上下文,这份 README 就是你的入口:读完它你应该知道目标、现状、环境、和怎么接着干。

与 `docs/` 的分工:`docs/` 放**沉淀后、给实现用**的结论;`research/` 放**研究过程、原始材料、
逆向草稿、社区知识库**。结论稳定后从 research 回填到 docs。

## 当前主题:SHT(自机 / shoot type)格式

THTK-Studio 要给东方的 SHT 文件做 IDE 支持。SHT 不是脚本语言,而是**纯二进制配置文件**(逐版本
差异大),所以 IDE 里应是**结构化表单/表格编辑器**,不是 Monaco + 编译。偏好**新作(TH18/TH19)**。

**字节布局**已基本搞清(见下文 docs 两篇);**TH16 运行时语义已基本攻下**(`func_*` 索引→行为表、
`flags`=运行时不读、shooterset 组织、自机弹伤害管线——社区此前无人公开破解,见 `sht/findings/` + `shared/`)。
**下一步**:TH18/TH19(偏好新作,需用户放样本)或深挖 TH16 有名却语义空白的玩法系统(Bomb/Spellcard)。

> 注:本工作区已**不止 SHT**——`ecl/`(ECL 敌机/弹幕脚本 VM,核心已基本反完)、`bullets/`(弹幕引擎)、
> `funcs/`(MainMenu/函数级)、`anm/`(待开)都是子工作区;跨子系统的通用知识统一沉到 `shared/`。见目录地图。

## 目录地图

```
research/
├── CLAUDE.md                  # 以 research/ 为根打开时的项目说明(自包含:环境/规则)
├── README.md                  # ← 你在这(总索引/续作指南)
├── shared/                    # ★ 跨子系统/可引用知识(社区结论 + 引擎通用,findings 稳定后蒸馏来这)
│   ├── touhou-modding-sources.md   # 社区工具/人物/权威来源速查
│   ├── th16-engine-math.md         # 引擎数学/CRT(atan2/fmod/sin/cos/sqrt)/ZUN PRNG 语义表
│   ├── th16-main-loop.md           # 每帧主循环 + 子系统 on_tick 调度
│   ├── th16-archive-thai-lzss.md   # THA1 .dat 归档(zun 加密 + LZSS,全格式通用)
│   └── ghidra-mcp-tools.md         # ghidra-re MCP 工具目录(pinned/hidden)+ 我们自维护 fork
├── sht/                       # ★ SHT(自机/shoot type)格式 —— TH16 运行时语义已基本攻下
│   ├── README.md              # SHT 研究计划 + 上游 commit 记录
│   ├── vendor/ (gitignored)   # 参考仓库克隆:sht-webedit, shmupcc-sht
│   ├── findings/              # 逆向报告(带可信度分级):
│   │   ├── 00-METHOD-逆向记录纪律.md  · 01-runtime-semantics(总览/开放问题)
│   │   ├── 03-funcstar-jumptables(★ func_* 跳转表+索引→行为) · 04-shot-runtime-architecture
│   │   ├── 05-flags-no-runtime-read(★ 字段全图+flags 证负) · 06-engine-incisions(切口地图)
│   │   ├── 07-shooterset-organization(火力×聚焦+主弹/子机弹) · 08-player-damage-pipeline
│   │   └── 99-QUIRK(判定半径哑弹)〔09-archive 已移到 shared/th16-archive-thai-lzss.md〕
│   ├── test-laser/           # 档1 实验:thcrap code-cave 重指 tick 槽注入追踪激光(cave 源码+patch+对抗审计)
│   └── disasm/               # Ghidra 工作区:README(★环境/策略)+ scripts/(run.sh) + samples//ghidra_projects//exports/ (gitignored)
├── ecl/                       # ★ ECL(敌机/弹幕脚本)VM —— VM 核心已基本反完;先读 07-vm-architecture(capstone)
│   ├── 00 格式 · 01 变量/上下文 · 02 运行时结构 · 03 vs ExpHP · 04 解释循环 · 05 开火接缝 · 06 自定义指令 · 07 总览 · ECL-info
│   └── vendor/th-re-data (gitignored)  # ★★ ExpHP TH16 符号金矿(逐版本 funcs/statics/structs);用 funcs/import_th_re_data.py 套进 Ghidra
├── bullets/                   # 弹幕引擎:01-core-engine · 02-bullet-vm-model(弹运动 VM) · 03-lasers
├── anm/                       # ANM(精灵动画)VM —— 占位/待系统开工
├── msg/                       # ★ MSG(对话/文本)系统 —— 占位/待系统开工(IDE 目标格式,空间大;入口 GuiMsgVm)
├── funcs/                     # 函数级工作:mainmenu/(MainMenu 反汇编) · unexplored.md(待挖图) · th-re-data 导入/dump 脚本
└── files/ (gitignored)        # TH16 th16.exe + .sht 资产 + Ghidra 工程(版权,用户本地提供)
```

相关 `docs/`(已沉淀):
- `docs/sht-format-research.md` — SHT 格式高层调研(代表什么、版本差异、工具现状)
- `docs/sht-webedit-and-shmupcc-analysis.md` — 两个参考仓库的源码级分析 + Rust 移植建议

## 环境(已搭好并验证,无 sudo,用户空间)

逆向工具链已就绪(详见 `sht/disasm/README.md`,也记在自动 memory `ghidra-re-toolchain`):

- conda 环境 `ghidra`:openjdk 21 + python 3.11 + pyghidra 3.1.0。
- Ghidra 12.1.2 在 `/data/sunyunbo/opt/ghidra_12.1.2_PUBLIC/`。
- **MCP 方式(推荐)**:装了 `re-mcp-ghidra` 并以 `claude mcp add ghidra-re`(local scope)注册进
  Claude Code,`claude mcp list` 显示 ✓ Connected。**新会话里 `ghidra-re` 的工具(反编译/xref/
  struct/搜索)应已加载**,可直接调用驱动 Ghidra。
- 脚本方式:`sht/disasm/scripts/run.sh <exe> <script.py>`(pyghidra,已验证)。
- **★★ 命名金矿(逆向先翻它)**:`ecl/vendor/th-re-data`(ExpHP,gitignored)= TH16 逐版本 **funcs/statics/结构体**;
  跑 `funcs/import_th_re_data.py` 一键套进 Ghidra(safe 不覆盖已有名)。**逆向 exe 第一件事就翻它,省掉大量从零命名。**
  当前 `th16` 工程已套用并落盘;详见 `shared/touhou-modding-sources.md` 的金矿条目。
- ⚠️ Ghidra 12 无 Jython,`.py` 必须走 PyGhidra;analyzeHeadless 工程目录必须绝对路径。

## 怎么接着干(给新会话)

> **现状(TH16,2026-06-11)**:func_* 跳转表 + 索引→行为全表、自机射击/本体、flags(证负)、header/shooter
> 字段图、**shooterset 组织(07)**、**自机弹伤害管线(08)** 均已破。**引擎数学/CRT/PRNG** → `shared/th16-engine-math.md`;
> **THA1 .dat 归档** → `shared/th16-archive-thai-lzss.md`;**ECL VM 核心** → `ecl/`(07 capstone);**弹幕引擎** → `bullets/`。
> 其余切口(敌人/道具/图形/音效)索引见 `findings/06-*`。**下一步**:换 TH18/19(需样本)或深挖 TH16 玩法系统(Bomb/Spellcard)。

1. 确认有样本:`research/sht/disasm/samples/`(TH18/19)或 `files/`(TH16,用户已放 th16.exe)。没有就先问用户。
2. 接着挖 → 先读 `findings/06-*`(切口地图)定位锚点;原理/纪律读 `00-METHOD-*` + `sht/disasm/README.md`。
   换新作做 SHT → 读 `01-runtime-semantics.md` 开放问题 + `03-*` 的锚点常量法。
3. 用 `ghidra-re` MCP 工具(或 run.sh + 脚本)按锚点常量定位 SHT 解析器:
   - shooterset 终止符 `0xFFFFFFFF`、`forced_shtoffarr_len=0x28`、`option_pos_len=0xA0`、`max_opt=4`;
   - 按 TH18/19 已知 shooter 步长找遍历循环 → 顺 `func_on_tick` 找跳转表 → 逐个反编译命名。
4. 新发现 → 先进 `sht/findings/`(过程)与 `shared/`(可信社区结论);稳定后回填 `docs/`。

## 纪律(开不开新 repo、要不要开源都要守)

- **主仓库不留任何版权字节**:游戏 exe、游戏资产、大段反编译原文一律 gitignore。
- 可发布的规格结论 → `docs/` 与 `shared/`;scratch(exe、工程、dump、vendor)→ gitignore。
- 这样将来若决定把 `research/` 切成独立 repo / 开源 IDE,几乎零成本(见关于是否拆分的权衡讨论)。
