# research/sht/disasm — 东方本体反汇编工作区

目标:用反汇编 + 社区资料,解开 `findings/01-runtime-semantics.md` 里没人公开破解的语义黑洞——
逐版本 `func_on_init/tick/draw/hit`(行为函数索引)、`flags` 段位含义、`unknown_*` 字段。

## 环境(Linux 服务器,无 sudo,用户空间)— ✅ 已验证可用

- **conda 环境 `ghidra`**:`openjdk 21` + `python 3.11` + `pyghidra 3.1.0`(JPype 1.5.2)。
- **Ghidra**:12.1.2,解压在 `/data/sunyunbo/opt/ghidra_12.1.2_PUBLIC/`(仓库外,不入库)。
- **关键环境变量**(脚本里已封装):
  - `GHIDRA_INSTALL_DIR=/data/sunyunbo/opt/ghidra_12.1.2_PUBLIC`
  - `JAVA_HOME=/data/sunyunbo/miniconda3/envs/ghidra`
- ⚠️ **Ghidra 12 已移除 Jython**,`.py` 脚本必须走 **PyGhidra(CPython 3)**,不能再靠
  `analyzeHeadless -postScript foo.py`(会报 "Ghidra was not started with PyGhidra")。
- 验证:`pyghidra tools/thecl.exe scripts/list_functions.py` → 正确分析出 921 个函数。
- binutils(objdump 支持 `pei-i386`/`pei-x86-64`)作为快速辅助随时可用。

## 样本(必须你提供)

东方游戏本体 exe 是 ZUN 版权商业软件,**不在仓库、不能下载**。请把**自己合法持有**的
`th18.exe` / `th19.exe`(32 位 PE)拷到 `samples/`(已 gitignore)。为互操作做个人逆向是社区惯例。

- 优先 TH18/TH19(用户偏好新作)。
- exe 基本无壳无强加密(加密在 .dat,exe 本体可直接静态分析),Ghidra 可直接吃。

## 用法(环境就绪后)

**首选:`scripts/run.sh`(PyGhidra,Python 3,已验证)** —— 对单个二进制跑一个脚本:

```bash
# scripts/run.sh <binary> <script.py> [args...]
research/sht/disasm/scripts/run.sh research/sht/disasm/samples/th18.exe \
  research/sht/disasm/scripts/find_sht.py
```

`run.sh` 已封装好 `GHIDRA_INSTALL_DIR` / `JAVA_HOME` 并调用 `pyghidra`。pyghidra 首次会对 exe
建临时工程并自动分析(大 exe 数分钟),脚本里 `currentProgram`、`getFunctionManager()`、
反编译 API 等全部可用(标准 GhidraScript API,只是 CPython 3 语法)。

**批量/复用已分析工程**:用 `analyzeHeadless` 先 `-import` 建工程并分析一次,后续
`-process <bin> -noanalysis` 复用。注意 **工程目录必须是绝对路径**(Ghidra 不接受以 `.` 开头的
路径),且 `.py` 后处理脚本仍需 PyGhidra 模式;纯 Java(`.java`)脚本则可直接用 analyzeHeadless。

## MCP 方式:让 Claude Code 直接驱动 Ghidra(已装,推荐用于迭代逆向)

装了 **`re-mcp-ghidra`**(jtsylve,headless,基于 pyghidra),把 Ghidra 的反编译/反汇编/xref/
struct/搜索等暴露成 MCP 工具,Claude Code 可直接调用,免去"写脚本→跑→解析 stdout"。

- 安装:`uv tool install re-mcp-ghidra`(隔离环境,自带 py3.12);可执行
  `~/.local/bin/re-mcp-ghidra`。后端检测:`re-mcp-ghidra backends` → `ghidra`。
- 已注册进 Claude Code(**local scope**,不入库,记录在 `~/.claude.json` 本项目条目):
  ```bash
  claude mcp add ghidra-re \
    -e GHIDRA_INSTALL_DIR=/data/sunyunbo/opt/ghidra_12.1.2_PUBLIC \
    -e JAVA_HOME=/data/sunyunbo/miniconda3/envs/ghidra \
    -- /data/sunyunbo/.local/bin/re-mcp-ghidra stdio
  ```
- `claude mcp list` 显示 `ghidra-re: ✓ Connected`。
- ⚠️ **新增 MCP 服务器的工具要新开一个 Claude Code 会话才会加载**;当前会话注册后仍调不到。
- 关系:这是**我们 dev 期逆向用的 MCP**,与 THTK-Studio 自己内置要 ship 的 MCP 服务器无关,
  且 local scope 不会写进项目 `.mcp.json`。

## 逆向策略(怎么从一坨汇编里找到 func_* 的含义)

不靠运气,靠格式已知量当"锚点"反推:

1. **定位 SHT 解析器**:用我们已知的版本常量做特征搜索——
   - shooterset 终止符 `0xFFFFFFFF`(4×0xFF)的比较;
   - 偏移表定长 `forced_shtoffarr_len`(TH18/19 = 0x28)、`option_pos_len`(0xA0)、`max_opt`(4);
   - main 头部移动速度等 float 的加载序列。
   命中后即为读取 SHT 结构、构造 shooter 对象的代码。
2. **锚定 shooter 结构步长**:用 `docs/sht-webedit-and-shmupcc-analysis.md` 里 TH18/19 的逐字段
   偏移表,找到按该步长遍历、并在已知偏移处取 `func_*` 字段的循环。
3. **跟踪 func_* 的去向**:`func_on_tick` 等被当作**函数指针表索引 / switch 分派**使用。顺着索引找到
   跳转表,表里每个条目就是一个行为函数(寻的、加速、激光、命中音效…)。逐个反编译命名,产出
   "索引→行为"表。
4. **flags 段**:找读取 flags 各位/各项的代码,看每位喂给哪段逻辑,反推语义。
5. **交叉验证**:与 pytouhou(Gen-1)、thtk、Mddass(TH07/12/13)对照;社区已知的零散结论用来
   印证而非替代反汇编结果。

## 产出去向

- 原始大文件(反编译 dump、跳转表导出)→ `exports/`(gitignore)。
- 结论(索引→行为表、flags 位表)→ `findings/02-*.md`,稳定后回填 `docs/`。
- 可复用的 Ghidra 脚本 → `scripts/`(入库)。

## 法务/伦理

- 仅对**用户自有**游戏做互操作性逆向,产出是格式语义文档/IDE 支持,不分发游戏代码或资产。
- `samples/` 永不入库。
