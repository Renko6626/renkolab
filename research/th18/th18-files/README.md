# th18-files/ — TH18 的样本 exe + Ghidra 工程(独立于 th16)

> ★ **TH18 用的是和 TH16 完全不同的一套文件/工程**。这里放 `th18.exe` 和它自己的 Ghidra 工程,
> **不要和 th16 那套搞混**。本目录内的版权字节 / 工程缓存**全部 gitignore**(见 `../.gitignore`),
> 本 README 是唯一入库的、用来标位置的文件。

## 放什么(用户本地提供,不入库)

```
th18/th18-files/
├── th18.exe                 # ★ TH18 本体(32 位 PE,ZUN 版权,用户放进来)
└── ghidra_projects/         # th18 的 Ghidra 工程(MCP/driver 自动生成)
    ├── th18.exe.gpr / .rep
    └── ...
```

## 两套工程的位置对照(★别混)

| 作品 | exe 路径 | MCP `database_id` | headless driver 的 project-dir / project / program |
| --- | --- | --- | --- |
| **TH16** | `research/files/th16.exe` | `th16` | `research/files/ghidra_projects` / `th16.exe` / `/th16.exe` |
| **TH18** | `research/th18/th18-files/th18.exe` | **`th18`** | `research/th18/th18-files/ghidra_projects` / `th18.exe` / `/th18.exe` |

→ 它们是**两个独立的 Ghidra 库**:`open_database` 用不同 `file_path` + 不同 `database_id`,互不影响。
**可同时开两个库并排对照**(MCP 支持多库;`decompile_function` 指定 `database=th16` 或 `database=th18`),
但**结论各写各的**(th16 → `../../player/` 等;th18 → `../findings/`)。

## 开工(放好 th18.exe 后)

```bash
# 1) MCP: open_database  file_path=research/th18/th18-files/th18.exe  database_id=th18  → wait_for_analysis
# 2) 套 ExpHP th18 名字 + 结构体(headless driver,先 MCP close_database 释放锁;env 见 ../../funcs/README.md)
python funcs/import_th_re_data.py        ecl/vendor/th-re-data/data/th18.v1.00a \
    --project-dir research/th18/th18-files/ghidra_projects --project th18.exe --program /th18.exe
python funcs/import_th_re_data_structs.py ecl/vendor/th-re-data/data/th18.v1.00a \
    --project-dir research/th18/th18-files/ghidra_projects --project th18.exe --program /th18.exe
# 3) MCP 重开 th18 → 套 zPlayer*/zEnemyData* 到全局 → 反编译即具名字段
```

> 注:首次 `open_database` 会把 th18.exe 导入并在此目录建工程;之后 import 脚本对**同一个工程**(上表 project-dir)
> 操作。确保两者指向同一处,否则名字/结构体进了 A 工程、MCP 开的是 B 工程会"看不到"(这个坑在 th16 踩过)。
