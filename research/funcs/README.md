# funcs/ — TH16 函数追踪 / 待挖地图(新会话任务指导)

> 目的:TH16 共 **1764** 个函数,ExpHP th-re-data 只命名了 ~932(886 有意义),我们自己研究命名了一批。
> 这个文件夹**自动算出"谁都没命名的处女地"**,给新会话一张可挑选的任务地图,避免重复劳动。

> **状态(2026-06-10):📥 ExpHP 614 个可导名已全部批量导入并落盘**(`apply_th16_thredata_bulk_names.py`,
> GhidraProject driver + `proj.save()`;renamed=614 / fail=0)。现工程命名 **261→872**,importable **614→0**,
> `🔬 真·待挖`仍 **515**。**下一步已定:语义主攻 `MainMenu`**(do_title_screen/character_select/… 28 个已可读)。

## 看什么
- **`unexplored.md`** ← 主产物。总览 + 三个可操作清单:
  1. **📥 可从 ExpHP 导入(614)**:我们工程里还是 `FUN_`、但 ExpHP 已命名 → **先批量导名白得上下文**(AnmVm 45 / AnmManager 38 / Supervisor 22 …)。
  2. **🔬 真·待挖(515)**:我们和 ExpHP 都没命名(非 CRT)= **真正的研究处女地**,按大小排 + 子系统线索。
  3. **🔬 待挖按子系统聚合**:挑一片(如 AnmVm/Arcfile/SoundManager/ReplayManager)整体挖。

## 怎么用(新会话)
1. **想要可读性最大化** → 先做"📥 可导入"那 614 个:写个脚本读 ExpHP `ecl/vendor/th-re-data/data/th16.v1.00a/funcs.json`,
   对工程里仍 `FUN_` 的地址批量 `rename`(参考 `../sht/disasm/scripts/apply_th16_ecl_names.py` 的做法;函数名经 MCP rename+save 可落盘)。
   ⚠️ 机械活**写脚本别派 agent**(memory `re-workflow-fanout-cost`)。
2. **想做新研究** → 从"🔬 真·待挖"挑一个**大 + 高 xrefs + 子系统线索你关心**的(或挑一整片子系统),
   按 `../ecl/` 那套流程反(一手反编译 + 四源对照 + 落 Ghidra + 写 findings)。
3. 当前推荐主攻:**ANM VM**(AnmVm/AnmManager/AnmLoaded 三类合计待导入 95 + 待挖 45,且是缺的第三套字节码 VM,见 `../anm/`)。

## 重新生成(工程改动后刷新地图)
```
# 1) dump 当前工程函数快照(需先 MCP close_database 释放锁;conda ghidra 环境)
GHIDRA_INSTALL_DIR=/data/sunyunbo/opt/ghidra_12.1.2_PUBLIC \
JAVA_HOME=/data/sunyunbo/miniconda3/envs/ghidra \
/data/sunyunbo/miniconda3/envs/ghidra/bin/python funcs/dump_funcs.py     # -> funcs/th16-funcs.json
# 2) 交叉分类出待挖清单(纯 python3)
python3 funcs/build_worklist.py                                          # -> funcs/unexplored.md
# 3) 完事 MCP open_database 重开
```

## 文件
- **`import_th_re_data_structs.py`** ← ★ 导 ExpHP **类型定义**(structs/unions/enums/typedefs)。导名脚本**不导这些**。
  - **布局永远精确**:每成员要么具名字段,要么退化 `char NAME[size]` 仍保留字段名;结构体按"值内嵌"拓扑排序(指针→`void*`,不产生顺序约束);`own` 覆盖 `ext`。
  - 用法 A(纯 python 生成 C,喂 MCP `parse_type_declaration` 或 Ghidra CParser):`python funcs/import_th_re_data_structs.py <DATA_DIR> --emit-c`;`--check` 自检 size(实测 **288/288 通过**)。
  - 用法 B(PyGhidra driver headless 全量,**先 `MCP close_database` 释放锁**,env 同下"重新生成"):`... <DATA_DIR> --project-dir files/ghidra_projects --project th16.exe --program /th16.exe [--apply-statics] [--all-types]`。**默认只导 z* 游戏结构(158 个);`--all-types` 连 Windows/d3d 也导。**
  - ⚠️ **坑(已踩)**:Ghidra 的 `CParser.parse(header)` **不可靠落盘**(parse 不报错但类型没真进 program dtm)。本脚本用法 B 改成**程序化构建** `StructureDataType` + `dtm.addDataType(REPLACE_HANDLER)`(标准持久 API)→ 可靠。
  - **现状(2026-06-12):✅ 全部 158 个 z* 结构体已用法 B 导入并落盘**(types=158 fail=0,zEnemyData/zEnemy/zBullet/zItem/zGui/zLaser*/zStage/zSupervisor/zMainMenu/zEclVm… 全在,category `/`)。player/bomb/SHT 的应用(`PLAYER_PTR→zPlayer*`、`*_BOMB_PTR→zBomb*` + 函数签名)经 REPLACE 原地更新仍生效。见 `../player/05` §0.5。
- `import_th_re_data.py` / `apply_th16_thredata_bulk_names.py` — 导 ExpHP funcs/statics **名字**(已跑过 614 个)。
- `dump_funcs.py` — GhidraProject driver,dump 全函数(addr/name/size/xrefs/thunk)→ `th16-funcs.json`。
- `build_worklist.py` — 交叉 `th16-funcs.json` × ExpHP funcs.json,分类产出 `unexplored.md`(纯标准库)。
- `th16-funcs.json` — 工程函数快照(随研究推进会变;gitignore 与否随仓库策略,内容仅地址/名/大小,无版权字节)。
- `unexplored.md` — 待挖地图(本文档主产物)。

## 分类口径(build_worklist.py)
- **已命名**:工程名非 `FUN_` 且非 CRT 模式。
- **可导入**:工程名 `FUN_` 但 ExpHP 有意义命名。
- **真·待挖**:工程名 `FUN_` 且 ExpHP 也无有意义命名,且非 CRT、非 thunk。
- **CRT/库**:名匹配 CRT 模式(`_/__/FID_/scrt/operator/std/Unwind/...`)或 thunk/external。
- ⚠️ 个别 `FUN_` 可能是 Ghidra 没认出的 CRT,混进"真·待挖";反编译时自行判断。子系统线索 = 地址最近的 ExpHP 已命名函数前缀(粗略,仅定位区域)。

## 关联
- ExpHP 名库:`../ecl/vendor/th-re-data`(命名层,无语义)。
- 落盘/driver:memory `ghidra-mcp-save-broken`、`ghidra-re-mcp-tips`;纪律 `../sht/findings/00-METHOD-逆向记录纪律.md`。
- 已完成子系统:ECL `../ecl/` · 弹幕 `../bullets/` · 主循环 `../shared/th16-main-loop.md` · 数学/PRNG `../shared/th16-engine-math.md`。
