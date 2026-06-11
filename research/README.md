# research/ — 研究工作区(新会话先读这里)

本目录是 THTK-Studio 动手写代码之前的**研究/逆向工作区**。如果你是一个**新的 Claude 会话**、
没有之前对话的上下文,这份 README 就是你的入口:读完它你应该知道目标、现状、环境、和怎么接着干。

与 `docs/` 的分工:`docs/` 放**沉淀后、给实现用**的结论;`research/` 放**研究过程、原始材料、
逆向草稿、社区知识库**。结论稳定后从 research 回填到 docs。

## 当前主题:SHT(自机 / shoot type)格式

THTK-Studio 要给东方的 SHT 文件做 IDE 支持。SHT 不是脚本语言,而是**纯二进制配置文件**(逐版本
差异大),所以 IDE 里应是**结构化表单/表格编辑器**,不是 Monaco + 编译。偏好**新作(TH18/TH19)**。

**字节布局**已基本搞清(见下文 docs 两篇);**运行时语义**(`func_*` 行为函数索引、`flags` 段、
`unknown_*` 字段)社区至今没公开破解,需要**反汇编游戏 exe** 才能解开——这是当前主攻方向。

## 目录地图

```
research/
├── CLAUDE.md                  # 以 research/ 为根打开时的项目说明(自包含:环境/规则)
├── README.md                  # ← 你在这(总索引/续作指南)
├── shared/                    # 东方 modding 社区的沉淀结论(可信、可引用的知识库)
│   ├── README.md
│   └── touhou-modding-sources.md   # 社区工具/人物/权威来源速查
└── sht/
    ├── README.md              # SHT 研究计划 + 上游 commit 记录
    ├── vendor/ (gitignored)   # 参考仓库克隆:sht-webedit @98b8cca, shmupcc-sht @dcf1f91
    ├── findings/              # 我们自己的逆向报告(带可信度分级)
    │   ├── 00-METHOD-逆向记录纪律.md      # ★ 证据链五段模板(动手前读)
    │   ├── 01-runtime-semantics.md        # 已知结论 + 开放问题
    │   ├── 02-community-recheck-funcstar-flags.md  # 社区普查:func_*/flags 无公开表
    │   ├── 03-th16-funcstar-jumptables.md # ★ TH16 func_* 跳转表 + 索引→行为 + 字段词汇表
    │   ├── 04-th16-shot-runtime-architecture.md    # 每帧子弹派发链 + 对象模型
    │   ├── 05-th16-flags-no-runtime-read.md        # ★ flags 无人读 + header/字段全图 + 死字段
    │   ├── 06-th16-engine-incisions.md    # ★ 子系统切口地图(敌人/道具/图形/音效/数学起步包)
    │   └── 99-QUIRK-th16-可配置判定半径其实是哑弹.md  # 糗事:.sht 判定半径被 init 覆写
    └── disasm/                # Ghidra 反汇编工作区
        ├── README.md          # ★ 环境 + 用法 + 逆向策略(动手前必读)
        ├── scripts/           # Ghidra 脚本(run.sh 封装 pyghidra)
        ├── samples/ (gitignored)        # 游戏 exe 放这(版权,用户提供)
        └── ghidra_projects/ exports/ (gitignored)
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
- ⚠️ Ghidra 12 无 Jython,`.py` 必须走 PyGhidra;analyzeHeadless 工程目录必须绝对路径。

## 怎么接着干(给新会话)

> **现状(TH16,2026-06)**:func_* 跳转表、自机射击/本体、flags(证负)、SHT header/shooter 字段图均已破
> (03/04/05)。**数学/CRT 模块已完整解出** → **`shared/th16-engine-math.md`**(角度/向量几何、CRT atan2/fmod/floor/
> sin/cos、ZUN 16 位 PRNG 算法+周期+回放机制、常量实测;名已落 Ghidra 工程)。
> 其余切口(敌人/道具/图形/音效)索引见 **`findings/06-th16-engine-incisions.md`**;或换 TH18/19,从这里起步。

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
