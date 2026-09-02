# local/ — 本地样本与工程（**不入库**）

**纪律：本仓库不留任何版权字节。** 游戏 exe、解包资产、Ghidra 工程、第三方仓库克隆
一律只存在于这个目录，根 `.gitignore` 把 `local/*` 全部忽略，只保留本文件。

新会话/新机器上这里是空的——照下表自己放回去。

## 布局

```
local/
├── th16.v1.00a/          TH16《鬼形兽》
│   ├── th16.exe          md5 cb9caf54ce5738f70086e783ec88fd2a  (683,520 B)
│   ├── th16.dat          原始归档(77 MB)
│   ├── pl0*.sht          从 .dat 解出的自机配置 + 我们改造过的实验档
│   ├── e0*.msg staff*.msg 结局/staff roll 样本
│   ├── ghidra_projects/  ★ 主工程 th16.exe.{gpr,rep}
│   └── th16.exe_ghidra/  早期工程(已弃用,留档)
├── th18.v1.00a/          TH18《虹龍洞》
│   ├── th18.exe          md5 9969cac756098c1da05a81de45437a70  (847,360 B)
│   └── ghidra_projects/  ★ 主工程 th18.exe.{gpr,rep}
├── vendor/               第三方仓库克隆(只记来源，不转发源码)
│   ├── th-re-data/       ★★ ExpHP 逐版本符号金矿(funcs/statics/structs)
│   ├── thcrap/           ★ thcrap 一手源码(插件/breakpoint/binhack 机制的权威)
│   ├── thcrap-patches/   ★ ExpHP 的 17 个玩法补丁(零 DLL 的真实范例 + keystone 构建链)
│   ├── thpages/          ★ ExpHP 指令参考站源码(ANM 渲染管线/坐标系/MSG 指令表)
│   ├── thtk/             thecl/thanm/thmsg/thstd/thdat
│   ├── sht-webedit/      SHT 字节布局的社区事实标准
│   ├── shmupcc-sht/      另一个 SHT 参考实现
│   └── th16.eclm th16.eclmap
└── scratch/              smoke_test 工程等一次性产物
```

## 怎么放回去

1. **游戏 exe / .dat**：用你自己合法持有的副本，按上表哈希核对后放进对应版本目录。
   **不要去下载。**
2. **vendor 克隆**：各仓库上游 commit 记录在
   [`../engine/_shared/community-sources.md`](../engine/_shared/community-sources.md)，按记录重新 clone。
   两个 SHT 参考仓库**均无 LICENSE 文件**，正式移植/发布前需确认授权，故不直接提交其源码。
   ExpHP `th-re-data` 上游同样无 LICENSE——它的函数名可用于本地逆向，但不擅自转发。
3. **Ghidra 工程**：不必找回，用
   [`../tooling/ghidra/bootstrap.py`](../tooling/ghidra/bootstrap.py) 从 exe 重建
   （建库 → 分析 → 套 ExpHP 名 → 套结构体 → dump → 落盘）。

## Ghidra 工程与 MCP

`ghidra-re` MCP 的 `open_database` 直接指工程里的 exe：

| 版本 | `file_path` | `database_id` |
| --- | --- | --- |
| TH16 | `local/th16.v1.00a/th16.exe` | `th16` |
| TH18 | `local/th18.v1.00a/th18.exe` | `th18` |

MCP 支持多库并存，两个 `database` 可以**并排对照**同名函数（ExpHP 命名一致），
这是把 TH16 已反清楚的逻辑映射到 TH18 的主要手法——
但**只能参考逻辑，地址/偏移必须在目标 exe 上重取**
（[`../games/th18.v1.00a/port-plan.md`](../games/th18.v1.00a/port-plan.md)）。

## `vendor/th18_modkit`（发布仓库）

`Renko6626/th18_modkit` —— **mod 包发布仓库**：自带 thcrap（2024-11-06 stable）+ 勾选式启动器，
朋友 clone 下来放好 `th18.exe` 就能一键启动。renkolab 是开发仓库，产物往那边推：
patch 进 `thcrap/repos/Renko_1055/<id>/`，DLL 进 `mods/`（带 `.json` 侧车）。
它的 `thcrap/repos/nmlgc/base_tsa/th18*.js` 就是 `sites.py conflicts` 要对照的那份。
