# tooling/ghidra — Ghidra 工具链

版本无关的逆向工具。目标是把「拿到一个新 exe → 有一个可用的、已命名的 Ghidra 库」
这件事从半天压到一条命令。

## 一键起库

```bash
P=/data/sunyunbo/miniconda3/envs/ghidra
JAVA_HOME=$P GHIDRA_INSTALL_DIR=/data/sunyunbo/opt/ghidra_12.1.2_PUBLIC \
  $P/bin/python tooling/ghidra/bootstrap.py th18
```

[`bootstrap.py`](bootstrap.py) 串起五步：**建库 → headless 分析 → 套 ExpHP 函数/静态名
→ 套 ExpHP 结构体 → dump 函数清单 → 落盘**，末尾打印一段可直接粘进
`games/<版本>/INDEX.md` 的登记文本。

路径按约定推导（`local/<ver>*/` 下唯一的 exe、`ghidra_projects/`、
`local/vendor/th-re-data/data/<版本目录名>/`），不用逐个指定。
工程已存在时默认跳过分析（幂等），要重来加 `--reanalyze`；
`--dry-run` 只预览计数、不写库。

TH16 上的实测基线（2026-09-01）：`skipped=1185 missing=123`、`types=158 failed=0`、
1764 个函数。`applied=0` 正是幂等的证据。

## 环境（无 sudo，用户空间，已验证）

| 项 | 值 |
| --- | --- |
| Ghidra | 12.1.2，`/data/sunyunbo/opt/ghidra_12.1.2_PUBLIC/`（仓库外） |
| conda 环境 `ghidra` | openjdk 21 + python 3.11 + pyghidra 3.1.0（JPype 1.5.2） |
| `GHIDRA_INSTALL_DIR` | `/data/sunyunbo/opt/ghidra_12.1.2_PUBLIC` |
| `JAVA_HOME` | `/data/sunyunbo/miniconda3/envs/ghidra` |

⚠️ **两个坑**：

1. **Ghidra 12 移除了 Jython**，`.py` 必须走 PyGhidra（CPython 3）。
   `analyzeHeadless -postScript foo.py` 会报 "Ghidra was not started with PyGhidra"。
2. **analyzeHeadless 的工程目录必须是绝对路径**，不接受以 `.` 开头的相对路径。

## 目录

| 文件 | 用途 |
| --- | --- |
| [`bootstrap.py`](bootstrap.py) | ★ 一键起库（上文） |
| [`th-re-data.md`](th-re-data.md) | ★★ ExpHP 符号金矿的用法与待挖地图说明 |
| [`import_th_re_data.py`](import_th_re_data.py) | 套 funcs/statics 名字 + 注释（safe，不覆盖已有名） |
| [`import_th_re_data_structs.py`](import_th_re_data_structs.py) | 套结构体/枚举/typedef（布局精确，未知区域填带名占位） |
| [`dump_funcs.py`](dump_funcs.py) | 导出当前命名状态到 JSON |
| [`build_worklist.py`](build_worklist.py) | 对比 ExpHP 与本地命名，算出「谁都没命名的处女地」 |
| [`apply_th16_thredata_bulk_names.py`](apply_th16_thredata_bulk_names.py) | TH16 批量导名（历史脚本） |
| [`mcp-tools.md`](mcp-tools.md) | `ghidra-re` MCP 工具目录（pinned / hidden） |
| `run.sh` | 对单个二进制跑一个 pyghidra 脚本 |
| `scripts/` | 逐子系统的命名固化脚本（headless 可复现） |
| `patches/` | 我们给 MCP fork 打的补丁（见下） |

```bash
# run.sh <binary> <script.py> [args...]
tooling/ghidra/run.sh local/th18.v1.00a/th18.exe tooling/ghidra/scripts/list_functions.py
```

`scripts/` 里的 `apply_th16_*_names.py` 是**唯一能给数据符号真改名**的途径
（MCP 的 rename 对数据符号需经 driver 落盘），且 headless 可复现。

## MCP：让 Claude Code 直接驱动 Ghidra（推荐用于迭代）

`ghidra-re` 把反编译/反汇编/xref/struct/搜索暴露成 MCP 工具，免去
「写脚本 → 跑 → 解析 stdout」。用的是**自维护 fork**
`Renko6626/re-mcp@thtk-patches`（上游 `jtsylve/ida-mcp` 基本不维护）。

```bash
uv tool install --force \
  "git+https://github.com/Renko6626/re-mcp@thtk-patches#subdirectory=packages/re-mcp-ghidra"

claude mcp add ghidra-re \
  -e GHIDRA_INSTALL_DIR=/data/sunyunbo/opt/ghidra_12.1.2_PUBLIC \
  -e JAVA_HOME=/data/sunyunbo/miniconda3/envs/ghidra \
  -- ~/.local/bin/re-mcp-ghidra stdio
```

- **fork 不在本仓维护**——它有自己的仓库和 upstream remote，吸收进来会打断跟上游 rebase、
  那条安装 URL、以及同仓的 `re-mcp-ida`/`re-mcp-core` 两个包。随用随取。
  [`patches/`](patches/README.md) 留着我们打过的补丁存档。
- ⚠️ **新增 MCP 服务器的工具要新开一个会话才会加载**；当前会话注册后仍调不到。
- ⚠️ **跑 `dump_funcs.py` 等 driver 前先 `close_database`**，否则撞工程锁。
- 这是**我们 dev 期逆向用的 MCP**，与 THTK-Studio 自己要 ship 的 MCP 服务器无关
  （local scope，不写进项目 `.mcp.json`）。

## 样本

游戏 exe 是 ZUN 版权商业软件，**不在仓库、不要下载**。放进 `local/<版本>/`，
见 [`local/README.md`](../../local/README.md)。exe 本体无壳（加密在 `.dat`），Ghidra 可直接吃。

## 产出去向

| 产物 | 去处 |
| --- | --- |
| 反编译 dump、跳转表导出等大文件 | `local/`（gitignore） |
| 结论（索引→行为表、字段图） | `engine/<子系统>/<版本>/`，见 [`METHOD.md`](../../METHOD.md) |
| 可复用脚本 | 本目录（入库） |

仅对**用户自有**游戏做互操作性逆向；产出是格式语义文档与工具支持，不分发游戏代码或资产。
