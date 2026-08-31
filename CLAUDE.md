# CLAUDE.md — renkolab

东方 Project 引擎逆向工作台。**先读 [`README.md`](README.md)**（结构与导航），
**动手前必读 [`METHOD.md`](METHOD.md)**（逆向记录纪律）与 [`DOCSTYLE.md`](DOCSTYLE.md)（文档规范）。
本文件只讲环境和跨层规矩。

## 层次归属：动手前先判断这一改属于哪层

| 层 | 装什么 | 轴 |
| --- | --- | --- |
| `engine/` | 引擎知识：运行时语义、字段图、opcode 表 | **子系统**为主，版本为辅 |
| `games/` | 每作的样本/工程登记、覆盖统计、待挖图 | 版本 |
| `mods/` | 改造产物：cave / patch / 成品脚本资产 | **版本**，死绑 exe build |
| `tooling/` | Ghidra 工具链 | 版本无关 |
| `local/` | exe、资产、Ghidra 工程、vendor（**gitignored**） | — |

三条容易犯的错：

1. **别在 `games/` 里写引擎结论。** 它只做登记和导航，正文指回 `engine/*`。
   一旦开始在那里写语义，版本轴就复辟了，这正是拆分前的病。
2. **新作特有机制是「子系统」，不是「版本目录」。** TH18 卡牌 → `engine/card/`，
   矩阵里 th16 一列填 ❌/❓ 即可。不要再开 `th19/` 这种国中之国。
3. **mod 产物不进 `engine/`。** cave 源码、patch、审计记录属于 `mods/<版本>/<mod名>/`。

## 环境（已搭好并验证，无 sudo；绝对路径）

- **Ghidra 12.1.2**：`/data/sunyunbo/opt/ghidra_12.1.2_PUBLIC/`
- **conda 环境 `ghidra`**：`/data/sunyunbo/miniconda3/envs/ghidra/`（openjdk 21 + python 3.11 + pyghidra 3.1.0）
  - `JAVA_HOME=/data/sunyunbo/miniconda3/envs/ghidra`
  - `GHIDRA_INSTALL_DIR=/data/sunyunbo/opt/ghidra_12.1.2_PUBLIC`
- **驱动 Ghidra 两条路**：
  1. **MCP（推荐迭代用）**：`ghidra-re`（自维护 fork `Renko6626/re-mcp@thtk-patches`，
     以 local scope 注册进 Claude Code）。工具目录见
     [`tooling/ghidra/mcp-tools.md`](tooling/ghidra/mcp-tools.md)。
     **fork 不在本仓维护**——它是 `jtsylve/ida-mcp` 的 fork，有自己的仓库和 upstream，随用随取。
  2. **脚本**：`tooling/ghidra/run.sh <exe> <script.py>`（封装好 env 的 pyghidra）。
- **新作一键起库**：`tooling/ghidra/bootstrap.py`（建库 → 分析 → 套 ExpHP 名 → 套结构体 → dump → 落盘）。
- ⚠️ **坑**：Ghidra 12 移除了 Jython，`.py` 必须走 **PyGhidra（CPython 3）**，
  不能 `analyzeHeadless -postScript foo.py`；analyzeHeadless 的工程目录**必须绝对路径**。

## 样本

游戏 exe 是 ZUN 版权商业软件，由用户放进 `local/<版本>/`（已 gitignore）。
**没有样本就先问用户，不要去下载。** 现有样本与工程见 [`local/README.md`](local/README.md)
和各作的 `games/<版本>/INDEX.md`。

## ★ 命名金矿（逆向一个新 exe 的第一件事）

`local/vendor/th-re-data`（ExpHP，gitignored）= 逐版本的 **funcs / statics / 结构体**。
`tooling/ghidra/bootstrap.py` 会自动套用（safe 模式，不覆盖已有名）。
**翻它能省掉大量从零命名**——详见 [`engine/_shared/community-sources.md`](engine/_shared/community-sources.md) 的金矿条目。

## 落笔纪律（完整版在 METHOD.md）

- 每条结论写全**发现 → 推测 → 验证 → 结论（可信度 + 版本）→ 证据（地址/出处）**。
- 一手反汇编 > 推断 > 社区单源，且必过「领域常识」关。
- **「超过社区」的宣称要过额外闸门**：一手到底 / 对抗证伪 / 量纲常识 / 交叉对名。复核前一律 🟡。
- 结论回流：`engine/<子系统>/<版本>/`（一手过程）→ `engine/<子系统>/OVERVIEW.md`（跨版本断言，附链接）。
- **地址写 `` `0x4919a0` ``（反引号、无 `@`）；文档开头声明默认版本**，跨版本文档里每个地址
  都要带前缀 `th16:`。写完跑 `python tooling/check-docs.py`。细则见 [`DOCSTYLE.md`](DOCSTYLE.md)。
- 涉及**手写机器码 / ABI** 的产出（cave、hook），必须上对抗审计——
  见 [`mods/_template/AUDIT-checklist.md`](mods/_template/AUDIT-checklist.md)。
