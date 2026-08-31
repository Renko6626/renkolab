# Ghidra 符号往返流程 — 设计

> **版本**：跨版本。本文出现的地址一律带版本前缀（如 `th16:0x442560`）。
> **状态**：设计已确认，待写实施计划（2026-09-01）。

## 0. 一句话

把「开库 → 导入 ExpHP 全量数据 + 我们自己的发现 → 逆向/做 mod → 存回仓库」
做成一条可重复、不丢东西的流水线：**ExpHP 那层随时可重放，我们那层进 git**。

## 1. 问题

两个洞，都是实测出来的，不是设想的。

**洞一：我们的成果存不住。** Ghidra 工程在 `local/`，而 `local/*` 是 gitignored 的
（[`.gitignore`](../../../.gitignore) 第一条：仓库不留版权字节）。所以「把 `zAbilityManager*`
绑到 `AbilityManager::on_tick` 的 this 参数」这种成果只活在本地 DB 里——换台机器就没了，
`bootstrap.py --reanalyze` 一跑也没了。ExpHP 那层能靠
[`bootstrap.py`](../../../tooling/ghidra/bootstrap.py) 重放，我们这层不能。

**洞二：ExpHP 的数据只导入了一半。** `local/vendor/th-re-data/data/<版本>/` 每作 9 个 JSON，
现有工具只吃了 3 个半。最大的漏是 `labels.json`（th18 有 492 条，一行没读）。

这两个洞叠起来的后果：DB 既不完整，又不可重建——**流程的两头都是断的**。

## 2. 两层模型

这是整个设计的骨架。**两层，两种寿命，两个方向。**

| | ExpHP 层 | 我们的层 |
| --- | --- | --- |
| 来源 | `local/vendor/th-re-data/`（gitignored） | 我们在 Ghidra 里干的活 |
| 方向 | **只进不出** | **双向** |
| 落盘 | 不入库 | `games/<版本>/symbols.json`，**入库** |
| 重建 | 从 vendor 克隆重放 | 从仓库文件回放 |

ExpHP 层不入库的理由是硬的：`th-re-data` 上游**无 LICENSE**，
[`local/README.md`](../../../local/README.md) 已写明「函数名可用于本地逆向，但不擅自转发」。
所以导出时必须把与 ExpHP 逐字相同的条目剔掉——见 §5。

## 3. ExpHP 数据盘点（实测 th18，2026-09-01）

| 文件 | th18 条数 | 现状 | 处置 |
| --- | --- | --- | --- |
| `funcs.json` | 729 | ✅ 已用 | 不变 |
| `statics.json` | 154 | ⚠️ 只用了名字 | 补 `type` 字段 |
| `type-structs-own.json` | 157 | ✅ 已用 | 补 `zCOMMENT` 注释回收 |
| `type-structs-ext.json` | 111 | ⚠️ 被 `game_only` 滤掉 | 维持（Windows/d3d，做渲染 hook 再说） |
| `type-aliases.json` | 122 | ✅ 间接用于解析类型串 | 不变 |
| `type-enums.json` | 10 | ❌ `game_only` 整个置空 | 放宽粒度：按 `z` 前缀留 |
| `type-bitfields.json` | 2 | ❌ 一行没读 | 新增导入 |
| `type-unions.json` | 0 | — | th18 为空，代码路径保留 |
| `labels.json` | **492** | ❌ **一行没读** | **新增导入**，见 §6 |

`type-bitfields.json` 只有 th18 有（th16/th17 均为 0），是 th18 独有资产。

## 4. 组件

### 4.1 新增

| 文件 | 职责 |
| --- | --- |
| `tooling/ghidra/create_missing_funcs.py` | 已写好并验过：在 ExpHP 标了函数、Ghidra 没建函数的地址上补建 |
| `tooling/ghidra/import_th_re_data_labels.py` | 导入 `labels.json`：VM dispatch 函数体内的 opcode case 标签 |
| `tooling/ghidra/symbols.py` | 我们那层的 `export` / `apply` / `status` 三个子命令 |
| `games/<版本>/symbols.json` | 我们那层的落盘文件（入库） |

`create_missing_funcs.py` 已在 th18 上实测：`created=62 existed=666 inside=1 failed=0`，
随后重跑名字导入 `applied=62`，ExpHP missing 从 63 降到 1
（`life_before_main__sub_48e43b`，CRT 初始化器，落在别的函数体内，无价值）。

### 4.2 改动

**`import_th_re_data_structs.py`** 四处：

1. **`--overwrite` 的 clear-mode bug**。现在 `--overwrite` 只放开了「跳过已定义数据」那道闸，
   底下仍是 `ClearDataMode.CLEAR_ALL_UNDEFINED_CONFLICT_DATA`——清不掉**已定义**的数据，
   异常被 `except: pass` 吞掉。后果：th18 的 58 个 `VTABLE_CARD_*` 至今是自动分析猜的
   `pointer[21]`，套不上 `zVTableCard`。改成 `CLEAR_ALL_CONFLICT_DATA`。
2. **enums 粒度**。`game_only=True` 现在直接 `enums = {}`，把 `zMainMenuId`（21 项）和
   `zMenuInput`（8 项）一起扔了。改成按 `z` 前缀留，其余（PE/Win32 那 8 个）继续扔。
3. **bitfields**。新读 `type-bitfields.json`，建成 Ghidra 位域类型。
4. **`zCOMMENT` 伪字段回收**。ExpHP 用零长度字段当注释写，th18 有 17 处。现在被
   `size <= 0: continue` 静默跳过——**结果对，但知识丢了**。改成落成该结构体的字段注释。

**`bootstrap.py`**：串成 §7 的九步。

## 5. `symbols.json` 与「谁的东西」判定

### 5.1 格式

一个版本一个文件，条目按地址排序（保证 git diff 可读）。

```json
{ "version": "th18.v1.00a",
  "exe_md5": "9969cac756098c1da05a81de45437a70",
  "funcs":    [{"addr": "0x408640", "name": "AbilityManager__on_tick",
                "cc": "__fastcall", "proto": "void f(zAbilityManager *self)",
                "comment": "每帧驱动卡牌链表；见 engine/card/th18/cards-01"}],
  "statics":  [{"addr": "0x4cf410", "name": "PLAYER_PTR", "type": "struct zPlayer*"}],
  "labels":   [{"addr": "0x430e14", "name": "ecl__case_424__moveSetMirror"}],
  "comments": [{"addr": "0x430ddb", "kind": "plate", "text": "…"}],
  "structs":  {"zAbilityManager": {"0x40": {"name": "anm_slot_flipped", "type": "int32_t",
                                            "note": "ExpHP 标 char[4]，实为 int"}}} }
```

`exe_md5` 是硬闸：**对不上直接拒绝 apply**。地址死绑 build，这个必须拦。

`structs` 只记**差异槽**，不记整个结构体——ExpHP 已有的那 157 个由第 4 步重建，这里只覆盖我们
改过的偏移。若某个结构体 ExpHP 完全没有（我们新反出来的），则该条目额外带 `"__size"` 字段，
`apply` 据此先建空壳再填槽。

存放位置选 `games/<版本>/`，因为它的轴就是版本，与旁边的 `INDEX.md`、`unexplored.md`
同属登记物。与 [`CLAUDE.md`](../../../CLAUDE.md) 「别在 `games/` 里写引擎结论」有擦边——
判断是那条规矩防的是**散文结论**，机器数据不算。若后续觉得别扭，改挂
`engine/_shared/symbols/` 只是换个路径常量。

### 5.2 判定规则

导出时现场与 ExpHP 数据 diff，**不在 DB 里打标记**。

| 丢掉 | 留下 |
| --- | --- |
| 与 ExpHP 逐字相同的名字 | 我们新起的名、我们改过的名 |
| Ghidra 默认名（`FUN_` / `DAT_` / `LAB_` / `thunk_`） | 任何函数原型、调用约定、全局类型绑定 |
| `[th-re-data]` 前缀的注释 | 我们写的注释 |
| 与 ExpHP 定义一致的结构体字段 | 字段名或类型与 ExpHP 不同的槽 |
| 与 `labels.json` 生成规则一致的标签 | 我们自己建的标签 |

原型 / 调用约定 / 全局类型绑定**一律留下**，因为 ExpHP 根本不提供这些——它给名字和结构体布局，
不给绑定。而正是绑定决定了反编译好不好读（§9 的验收里有实证）。

**为什么不用 `SourceType` 区分**：把 ExpHP 导入改成 `SourceType.IMPORTED`、我们的用
`USER_DEFINED`，看似更干净，但现有 th18 库里两者已经**都是** `USER_DEFINED`，要重新分辨就得
`--reanalyze` 重建——而重建正是本设计要保护的东西。diff 法在现有库上立刻能用，不需要重建。

### 5.3 `apply` 的覆盖语义

我们这层**压过** ExpHP 层，用覆盖而非 safe 模式。理由：这层的存在意义就是订正 ExpHP
（比如那个其实是 int 的 `char[4]`），safe 模式会让订正永远落不下去。
因此 §7 的流水线里，`symbols.py apply` 必须排在所有 ExpHP 导入**之后**。

## 6. labels / enums / bitfields 导入

### 6.1 labels

格式 `<opcode>__<名字>`，落点是 VM dispatch 函数体内的 case 地址。语义有两处佐证：
`th-re-data/README.md` 明写 "labels I generated in some functions for switch cases"，
且在 th18 库上核过宿主函数，全部落在 dispatch 函数体内。标签名按 ExpHP README 自己给的
拼法构造：`<组>__case_<后缀>`。

| 组 | th18 条数 | 宿主函数 |
| --- | --- | --- |
| `ecl` | 242 | `th18:0x430d30` 175 条 + `EclRunContext__ecl_run` 67 条 |
| `anm` | 136 | `AnmVm__run` |
| `msg` | 36 | `GuiMsgVm__run` |
| `std` | 21 | `StageInner__run_std` |
| `card` | 57 | `AbilityManager__allocate_new_card` |

两个附带收益：

- **`th18:0x430d30` 我们库里还没命名**，但 ExpHP 在它体内标了 175 个 ECL opcode case。
  身份因此确定——ECL 指令分发器——光看 `funcs.json` 看不出来。导入器顺带在宿主函数上写一条
  plate 注释，登记「本函数含 N 个 `<组>` opcode case」。这是**我们从数据推出的**，不是转发。
- `engine/anm/` 至今标着「未系统开工」，而 `AnmVm__run` 的 136 个 opcode case 一直躺在
  这个文件里没人读。

**card 组不当结论用。** `engine/card/th18/cards-03-card-registry-dump.md` 是一手反出的
58 项注册表，ExpHP 这里是 57 条 ID→地址。两边独立得出，正好做
[`METHOD.md`](../../../METHOD.md) 要求的**交叉对名**：对得上就提可信度，对不上就有一边错了。
**先落库当参照，不改既有结论**——这是本设计范围外的一次独立复核任务。

### 6.2 enums

`zMainMenuId`（21 项）、`zMenuInput`（8 项）建成 Ghidra 枚举。其余 8 个是 PE 头部常量，扔掉。

### 6.3 bitfields

`zAnmBitfieldsHi` / `zAnmBitfieldsLo` 描述 ANM VM 的标志位布局
（`blend_mode`、`mirror_x`、`rotation_mode`、`slowdown_immune` …）。

**绑定关系是推测，不是事实**：`type-structs-own.json` 里没有任何字段以这两个类型为类型，
但 `zAnmVmPrefix` 有 `flags_lo` / `flags_hi` 两个 `int32_t`（偏移 `0x534` / `0x538`），
按 Lo/lo、Hi/hi 的名字对应。**故导入器只建类型、不自动绑定**；绑定要在 `AnmVm__run` 上
读位运算验证过，验过之后它属于**我们那层**，进 `symbols.json`。这条按 METHOD.md 的
五段链走，验证前一律 🟡。

## 7. bootstrap 流水线

现 5 步，改 9 步：

```
0  漂移拦截：symbols status 若有未导出项则中止        （仅 --reanalyze 时）
1  建库 + headless 分析
2  补建 ExpHP 标了而 Ghidra 没建的函数                 create_missing_funcs.py
3  套 ExpHP 函数名 / 静态名                            import_th_re_data.py
4  套 ExpHP 结构体 + 枚举 + 位域 + statics 类型         import_th_re_data_structs.py
5  套 ExpHP labels                                     import_th_re_data_labels.py
6  回放我们自己的层                                    symbols.py apply
7  dump 函数清单                                       dump_funcs.py
8  汇总
```

顺序不是随意的：第 2 步必须在第 3 步前（否则 ExpHP 名字落不上，实测漏 63 个）；
第 5 步要求函数已存在；第 6 步必须垫底（§5.3）。

第 0 步是本流程唯一的安全网。导出定为**手动**，那 `--reanalyze` 就是最危险的一条路径——
它会炸掉 DB。所以只在这条路径上硬拦：有未导出的东西就中止，让人先 `export`。

## 8. 锁

MCP `ghidra-re` 开着库时，driver 脚本会撞工程锁
（[`tooling/ghidra/README.md`](../../../tooling/ghidra/README.md) 已有这条警告）。
所有 driver 统一捕获该异常，报一句人话：先在 MCP 里 `close_database`。

## 9. 验收

没有测试框架可挂，用实库自证。**五条全绿才算跑通**：

1. `export` 之后 `status` 报 0 漂移。
2. `apply` 幂等：紧接着再跑一次，改动数为 0。
3. **备份现有 th18 工程 → `--reanalyze` 全流程重建 → `status` 对比重建前的导出文件，0 漂移。**
   这条才真正证明「往返」成立，前两条只证明单向自洽。
4. labels 导入后计数对得上：`anm` 136、`ecl` 242、`msg` 36、`std` 21、`card` 57。
5. `python tooling/check-docs.py` 全绿。

另有一条**可读性实证**（非自动化，人看）：给 `AbilityManager__on_tick` 绑上
`zAbilityManager*` 后，`*(int *)((int)param_1 + 0x3c)` 应变成 `(self->__id_3c).id`、
`+0x38` 变成 `self->selected_active_card`。这个转换已在事务里试过并回滚，效果确认，
只是成果还存不住——正是本设计要解决的。

## 10. 取舍与风险

| 决定 | 代价 | 为什么仍这么定 |
| --- | --- | --- |
| 导出手动，不加 git 钩子 | 可能忘 | 钩子要每次 commit 起 JVM 开库（几十秒）；改用 `status` 对账 + `--reanalyze` 硬拦 |
| `symbols.json` 放 `games/` | 与「games 只做登记」擦边 | 轴对（版本），且是机器数据不是散文结论；改路径成本极低 |
| 用 diff 分辨归属，不用 `SourceType` | 每次导出都要读 vendor | 现有库两者都是 `USER_DEFINED`，改 SourceType 需重建，而重建正是要保护的 |
| `--overwrite` 改用 `CLEAR_ALL_CONFLICT_DATA` | 真会覆盖已有数据定义 | 仅在显式传 `--overwrite` 时生效；被覆盖的是自动分析的猜测，不是人工成果 |
| bitfields 只建类型不绑定 | 还得再干一次活 | 绑定是推测（§6.3），未验证前不落成事实 |

## 11. 实施记录：与本设计的偏差（2026-09-01 当天实现）

实现时撞出五处设计没料到的东西，都已落进代码，记在这里免得下次重新踩。

**① §5.2 说「不用 `SourceType` 区分」——那句话现在不准确。** 实际需要**两道**判据，
它们回答的是不同问题：

| 判据 | 分辨什么 |
| --- | --- |
| `SourceType == USER_DEFINED` | **人写的** vs **分析器产的**（FunctionID / demangler / RTTI / switch 分析） |
| 与 ExpHP 数据 diff | **我们的** vs **ExpHP 的**（两者都是 `USER_DEFINED`，SourceType 分不开） |

设计当初只想到第二道。少了第一道，导出会混进 602 个 RTTI `vftable` 符号、
543 条 `Library Function -` 注释和一堆 `switchdataD_*`。两道叠起来，
th18 的 3724 个候选筛到 **200 条真·我们的**。

**② 结构体基线必须模拟导入器的顺序追加，不能按声明偏移建表。**
`StructureDataType.add()` 不认声明偏移，只顺序追加；而 ExpHP 有些结构体的行是乱序甚至
偏移重复的——th18 `zMainMenu` 在 `0x20` 上出现两次（`menu_state` 和 `select`），
于是实际落点从那里起整体错位 4 字节。基线若按声明偏移算，这个结构体会整片报成
「我们改的」：**24 个假阳性**。

顺带暴露一个**既有的导入精度问题**：`zMainMenu` 在库里的布局与 ExpHP 声明的并不一致。
根因是 ExpHP 的行本身有重复偏移，得先决定 `menu_state` 和 `select` 谁占 `0x20`——
这是对 ExpHP 意图的判断，**留给人决定，本次不动**。

**③ 分析器注释要单独一张正则表挡。** 注释没有 `SourceType`，只能按文本认。
th18 实测 1856 条里 1850 条是样板话（`Library Function -`、`IMAGE_THUNK_DATA32`、
`.*RTTI `、`Rsrc_* Size of resource:`、`meta pointer for`、`::vftable`…），
剩下 182 条 `pre` 注释才是人写的卡牌笔记。

**④ 位域类型排除在结构体 diff 外。** `zAnmBitfieldsHi/Lo` 的组件布局是 Ghidra 的位域
打包行为，没法在基线里廉价复现。代价：手改这两个类型导出会漏（就 2 个，认了）。
这一条是被第 0 步的漂移拦截**当场抓出来的**——它在重建前拦下了 10 个假阳性。

**⑤ 原型按结构存，不存 C 字符串。** `{"cc", "ret", "params":[{"name","type"}]}`，
回放时用 `DataTypeParser` 逐个解析。存 C 串就得在回放时解析完整声明，脆得多。

**⑥ statics 的指针类型要深解，不能沿用建结构体时的 `void*`。**
`to_dt` 把所有指针压成 `void*`，那是建结构体时的有意为之（免得 `struct A*` 在 A 之前出现
就造出拓扑环）。但套到全局上就把最值钱的信息扔了。加了一个 `to_dt_deep` 专供 statics：

```c
// 之前：PLAYER_PTR 是 void*
*(float *)((int)PLAYER_PTR + 0x624)
// 之后：PLAYER_PTR 是 zPlayer*
(PLAYER_PTR->inner).field_0
```

另：流水线实际是 **8 步 + 第 0 步**（漂移拦截只在 `--reanalyze` 时出现），不是 §7 写的 9 步。

### 验收结果（2026-09-01，th18 实测）

| # | 条目 | 结果 |
| --- | --- | --- |
| 1 | `export` 后 `status` 报 0 漂移 | ✅ |
| 2 | `apply` 幂等（再跑一次改动为 0） | ✅ `funcs=0` |
| 3 | **全量 `--reanalyze` 重建后 0 漂移** | ✅ 导出文件与重建前**逐字节一致** |
| 4 | labels 计数对得上 | ✅ 492（ecl 242 / anm 136 / msg 36 / std 21 / card 57） |
| 5 | `check-docs.py` 全绿 | ✅ |

重建后函数数与重建前一致（2333 / 已命名 1366），分析是确定性的。

## 12. 不做什么

- **不碰 mod 侧产物**。cave / patch / 审计记录留在 `mods/<版本>/`，与符号层无关。
- **不做多版本符号迁移**（th16 结论自动搬到 th18）。
  [`games/th18.v1.00a/port-plan.md`](../../../games/th18.v1.00a/port-plan.md) 已定调：
  地址偏移一律重取，自动迁移只会制造假事实。
- **不导入 `type-structs-ext.json`**（Windows/d3d 结构）。做渲染 hook 时再开
  `--all-types`，现在是噪音。
- **card 组交叉对名不在本设计内**，见 §6.1。
