# CLAUDE.md — SHT 逆向研究工作区

> 本文件供**以 `research/` 为根目录打开**的研究 agent 使用。此时父级
> `/data/sunyunbo/www/THTK-Studio-2/CLAUDE.md` 和该项目的自动 memory **都不会加载**,所以这里
> 把环境与规则写成**自包含**的。先读 `README.md`(本目录),它是完整入口。

## 这是什么 / 目标

THTK-Studio 是一个东方 Project 脚本/资产 modding 的桌面 IDE。本工作区专做一件事:**搞懂 SHT
(自机 / shoot type)格式,尤其是反汇编游戏 exe 来解开运行时语义**,为 IDE 的 SHT 支持铺路。

- SHT 是**纯二进制配置文件**(逐版本差异大),不是脚本语言。
- **字节布局**已基本清楚(见 `../docs/sht-webedit-and-shmupcc-analysis.md`,在父仓库)。
- **运行时语义**——`func_on_init/tick/draw/hit`(行为函数索引)、`flags` 段、`unknown_*` 字段
  ——**社区至今无人公开破解**,需要反汇编 TH18/TH19 的 exe 才能解。**这是当前主攻方向。**
- 偏好**新作(TH18/TH19)**。

## 先读这些

1. `README.md`(本目录)— 总索引/续作指南。
2. `sht/disasm/README.md` — ★ 环境 + 用法 + **逆向策略**(动手前必读)。
3. `sht/findings/01-runtime-semantics.md` — 已知结论 + 开放问题(带可信度分级)。
4. `shared/touhou-modding-sources.md` — 社区工具/人物/权威来源,哪里查最准。

## 环境(已搭好并验证,无 sudo;以下为绝对路径)

- **Ghidra 12.1.2**:`/data/sunyunbo/opt/ghidra_12.1.2_PUBLIC/`
- **conda 环境 `ghidra`**:`/data/sunyunbo/miniconda3/envs/ghidra/`(openjdk 21 + python 3.11
  + pyghidra 3.1.0)。`JAVA_HOME=/data/sunyunbo/miniconda3/envs/ghidra`、
  `GHIDRA_INSTALL_DIR=/data/sunyunbo/opt/ghidra_12.1.2_PUBLIC`。
- **驱动 Ghidra 的两条路**:
  1. **MCP(推荐迭代用)**:已装 `re-mcp-ghidra` 并以 `ghidra-re`(local scope)注册进 Claude
     Code。新会话里 `ghidra-re` 的工具(反编译/反汇编/xref/struct/搜索)应已加载,直接调用。
     若没看到工具:`claude mcp list` 应显示 `ghidra-re ✓ Connected`;否则见 `sht/disasm/README.md`
     重新 `claude mcp add`。
  2. **脚本**:`sht/disasm/scripts/run.sh <exe> <script.py>`(封装好 env 的 pyghidra,已验证)。
- ⚠️ **坑**:Ghidra 12 移除了 Jython,`.py` 脚本必须走 **PyGhidra(CPython 3)**,不能用
  `analyzeHeadless -postScript foo.py`;analyzeHeadless 的工程目录**必须绝对路径**(不接受 `.` 开头)。

## 逆向策略(简版,详见 `sht/disasm/README.md`)

用格式已知量当锚点反推,别靠蒙:

1. 用常量定位 SHT 解析器:shooterset 终止符 `0xFFFFFFFF`、`forced_shtoffarr_len=0x28`(TH18/19)、
   `option_pos_len=0xA0`、`max_opt=4`、main 头部移动速度 float 加载序列。
2. 按 TH18/19 已知 shooter 步长找遍历循环,定位读取 `func_*` 字段处。
3. `func_on_tick` 等被当**函数指针表索引 / switch 分派**用 → 找到跳转表 → 逐个反编译命名 →
   产出"索引→行为"表。
4. 同法解 `flags` 各位。
5. 与 pytouhou(仅 Gen-1)、Mddass(仅 TH07/12/13)交叉印证,但**别外推到 TH15-19**。

## 样本

游戏本体 exe 是 ZUN 版权商业软件,由用户放进 `sht/disasm/samples/`(已 gitignore)。优先
`th18.exe`/`th19.exe`(32 位 PE)。没有样本就先问用户,**不要去下载**。

## 工作纪律

- **主仓库不留任何版权字节**:游戏 exe、游戏资产、大段反编译原文一律 gitignore
  (`samples/ ghidra_projects/ exports/ vendor/` 已配好)。只提交脚本 + markdown 结论。
- 结论回流路径:**`sht/findings/`(过程报告)→ `shared/`(可信社区结论,带出处/可信度/版本范围)
  → `../docs/`(父仓库,驱动 IDE 实现)**。`../docs/sht-*.md` 在父仓库,可用绝对路径写。
- 反汇编得到的结论务必标注**游戏 + 地址/函数 + 可信度**,便于复核。
- ★ **逆向记录纪律**:每条结论按 `sht/findings/00-METHOD-逆向记录纪律.md` 写全
  **发现→推测→验证→结论(可信度+版本)→证据(地址/出处)** 五段链;一手反汇编证据 > 推断 > 社区单源,
  且必过"领域常识"关(与游戏实际表现冲突先怀疑自己的映射)。
- 不确定就标 🟡/❓,别把推断写成定论。SHT 逐版本差异大,结论要注明适用版本。
- ★ **"超过社区"的宣称必须额外谨慎复核**:凡是我们声称**比现有社区资料(sht-webedit / pytouhou /
  wiki 等)更进一步**的结论(解开了它们标 `unknown` 的字段、推翻/细化了它们的命名、给出它们没有的运行时
  语义),都**没有外部佐证 = 风险最高**,必须按以下闸门复核后才能写成 ✅:
  1. **一手到底**:结论必须落到**具体地址 + 具体指令/读取点**;agent/二手报告说"读了某偏移"**不等于**
     "用途是 X"——用途要自己反编译确认(教训:把 agent 的"0x42f4e0 读 +0x08"脑补成"擦弹判定",实为射速)。
  2. **对抗证伪**:先假设自己错,主动找推翻证据(全字段取值分布、所有读取点、调用方),证伪不掉才保留。
  3. **量纲/常识关**:别把"代码 == 常量"当全貌——查该字段**在真实 .sht 里的取值分布**(教训:把 0x21
     当布尔 `==2`,实为按角色 {0,1,2,4};把 slot+0x60 当角度,实为速度,被游戏内实测纠正)。
  4. **交叉对名**:与社区字段名逐项核对;**冲突时优先怀疑自己**,对上了才说"反超"。
  - 复核前一律标 🟡;只解开了某分支别写成"整个字段已解"。**宁可少宣称,不可假宣称。**

## 与父项目的关系

本工作区是 THTK-Studio 的 dev 期研究,产出最终回流到父仓库 `../docs/` 和将来的
`../src-tauri/src/modules/sht/`。`ghidra-re` MCP 是**我们 dev 期逆向工具**,与 IDE 自己内置要 ship
的 MCP 服务器无关(local scope,不入库、不随产品分发)。
