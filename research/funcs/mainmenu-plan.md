# TH16 MainMenu 子系统逆向计划

> 版本:**TH16《鬼形兽》v1.00a**(`files/th16.exe`,imagebase `0x400000`)。仅此版本,勿外推。
> 目标子系统:`MainMenu`(标题/选项/键位/难度/角色/副季/练习/录像/音乐室/符卡练习 等所有标题菜单态)。
> 选它的理由:`🔬 真·待挖`里**累计字节最大的子系统**(15 函数 / 17.7KB,含全工程最大的
> `0x44c8c0` = 5034 字节);且 ExpHP 已给 28 个 `MainMenu__do_*` 锚点 + 3 个菜单结构体,
> **导航底图最全 = 性价比最高的语义首攻**。
>
> 写于 2026-06-10,批量导名(872 命名)完成后。纪律见 `../sht/findings/00-METHOD-逆向记录纪律.md`。

> **状态(2026-06-10):Phase 1–3 已完成,MainMenu 真·待挖 15→0(全清)。**
> - Phase 1 状态机骨架 → `mainmenu/01-state-machine.md`(on_tick 分派 + change_menu + 态枚举 0x00–0x14 全表)。
> - Phase 2 各态辅助函数 → `mainmenu/02-state-helpers.md`(14 个原 FUN_ 命名:选项/键位/录像/符卡练习子模型)。
> - Phase 3 ★SHT 回扣 → `mainmenu/03-character-subseason-sht-chain.md`(角色/副季选择 → `player_shot_init` → `.sht` 表 + `sht_parse_resolve_funcptrs`)。
> - **未做(可选收尾)**:Phase 0 把 `zMainMenu`/`zMenuHelper` 结构体套进工程 + 数据符号改名(`apply_th16_mainmenu_names.py`,driver 落盘);
>   深挖 `sht_parse_resolve_funcptrs` 的 func_* 解析(已接到门口,**交给 SHT 主线**)。

## 0. 为什么值得做(价值 + SHT 回扣)

- **状态机 + 可复用菜单控件**:整个引擎的菜单/光标/导航栈逻辑都在这里(`zMenuHelper`),反出来
  的 helper 在 PauseMenu 等处也复用 → 一次反、多处可读。
- **★ 与原 SHT 任务回扣**:`do_character_select` / `do_subseason_select` 正是玩家**选自机/副季**的地方
  = 决定**加载哪个 `.sht`/shottype 槽**的源头。摸清这条选择链,能把"菜单选择 → SHT 文件加载"
  接上,对 IDE 的 SHT 支持是真线索(留意:character/subseason → 写进存档/全局 → SHT 装载)。
- **清掉一大片处女地**:17.7KB 待挖一次性归零,worklist 显著缩短。

## 1. 已知锚点(动手前的地图;均 🟡 待一手复核)

### 1.1 对象模型(ExpHP `type-structs-own.json`,🟡 偏移待反编译坐实)
`zMainMenu`(size 0x5e00)关键字段 —— **这就是 on_tick 的状态机字段**:

| off | 字段 | 用途(推测) |
| --- | --- | --- |
| 0x00 | `vtable` (`zVTableMainMenu`) | |
| 0x08 / 0x0c | `on_tick` / `on_draw` (`zUpdateFunc*`) | 注册进 UpdateFuncRegistry 的每帧回调 |
| 0x10 / 0x14 | `title_anm` / `title_v_anm` (`zAnmLoaded*`) | 标题画面 anm |
| **0x18** | **`current_menu` (int)** | ★ **on_tick 据此 switch/分派到 do_\* 的状态枚举** |
| 0x1c | `previous_menu` | 返回上一级用 |
| 0x20 | `status` | |
| 0x24 / 0x28 | `selection` / `selection_on_prev_tick` | 当前光标项 |
| 0x30 | `selected_index_stack[0x10]` | 进出子菜单的**光标历史栈** |
| 0xb0 | `current_stack_index` | 栈深 |
| 0x804 | `music_room_data` (`zMusicRoomData`) | 音乐室 |
| 0x5b50 | `__replay_ptrs[0x19]` | 录像菜单条目指针表 |
| 0x5de4 | `thread` (`zThread`) | |

`zMenuHelper`(size 0xd8)= **可复用菜单控件对象**(高 xref 待挖函数最可能是它的方法):

| off | 字段 |
| --- | --- |
| 0x00 / 0x04 / 0x08 | `next_selection` / `current_selection` / `num_choices` |
| 0x0c | `stack_selection[0x10]` |
| 0x4c | `stack_num_choices[0x10]` |
| 0x8c | `stack_depth` |

`zMenuCommonThing`(size 0xd8,`zMainMenu` 别处也含 `+0x10c menu`,但那是别的类)—— 字段多 unknown,反时一并坐实。

### 1.2 已命名锚点(28 个 `MainMenu__*`,ExpHP 导入,名 🟡 语义待证)
- 骨架:`constructor 0x44a9f0` · `initialize 0x44ac70` · **`on_tick 0x44af80`(1368B,★分派器)** · `on_draw 0x44b530`。
- 各菜单态 `do_*`(按地址):`do_title_screen 0x44b5f0`(3864B)· `do_options 0x44c570` ·
  `do_key_config 0x44e930` · `do_difficulty_select 0x44fe20` · `do_character_select 0x4502c0` ·
  `do_subseason_select 0x450af0` · `do_practice_stage_select 0x450ef0` · `do_replay_menu 0x451750` ·
  `do_menu_sub_4532f0 0x4532f0` · `do_music_room 0x4546f0` ·
  `do_spell_practice__{stage_select 0x4553d0 / character 0x455790 / spellcard 0x455900 / subseason 0x455d50 / difficulty 0x456a20}`。
- 绘制:`on_draw__{practice_stage_select / replay / player_data / 4538b0 / 4541b0 / spell_practice_histories}`。

## 2. 待挖目标清单(15 个 FUN_,nearest-anchor=MainMenu;按字节降序)

| addr | size | xrefs | 推测(待反编译证实) |
| --- | --- | --- | --- |
| **0x0044c8c0** | 5034 | 3 | 紧接 `do_options`(0x44c89f)之后 → 选项菜单的**绘制/明细子逻辑**,或音量/画面设置态 |
| 0x0044dc70 | 3255 | 4 | 介于 options 与 key_config 之间 |
| 0x0044ec60 | 2725 | 4 | 紧接 `do_key_config`(0x44ec45)之后 → 键位绘制/应用 |
| **0x004560b0** | 2277 | **7** | ★高 xref → **跨菜单复用的 helper**(光标/条目列表/输入轮询);优先 |
| 0x0044f810 | 1540 | 2 | key_config↔difficulty 之间 |
| 0x00452c30 | 1011 | 3 | replay 相关簇内 |
| 0x00451560 | 475 | 1 | replay 簇 |
| 0x0044ad20 | 447 | 2 | 介于 initialize 与 on_tick → **子初始化** |
| 0x004545a0 | 331 | 1 | music_room 簇 |
| 0x0044f710 | 241 | 1 | difficulty 前 |
| 0x004569a0 | 119 | 4 | 高 xref 小函数 → 复用 leaf(clamp/取项数?) |
| 0x00455370 | 92 | 3 | spell_practice 簇复用 leaf |
| 0x00456060 | 80 | 1 | |
| 0x00455330 | 57 | 1 | |
| 0x0044af50 | 34 | 2 | 紧贴 on_tick 前 → trampoline/getter |

## 3. 分阶段执行

### Phase 0 — 把菜单结构体导进 Ghidra(机械,写脚本)
- 用 `parse_type_declaration` 把 `zMainMenu` / `zMenuHelper` / `zMenuCommonThing` / `zVTableMainMenu`
  建进工程(依赖 `zAnmLoaded`/`zUpdateFunc`/`zTimer`/`zThread`/`zAnmId`/`zMusicRoomData` 等;缺的先建占位或裁字段)。
- 给 `on_tick`/`do_*`/各 helper 的 this 指针套 `zMainMenu*` / `zMenuHelper*`。
- ⚠️ 结构体/数据符号改动 **MCP 不持久**,要写进 `../sht/disasm/scripts/apply_th16_mainmenu_names.py`
  (GhidraProject driver + `proj.save()`,参考本目录 `apply_th16_thredata_bulk_names.py`)。函数名/注释 MCP 可落盘。

### Phase 1 — on_tick 状态机骨架(先解分派)
1. 反 `MainMenu__on_tick`(0x44af80):确认它读 `this+0x18 current_menu`(证实/证伪 §1.1 假设),
   找 **switch / 跳转表 / if 链** → 建立 **`current_menu` 枚举值 → `do_*` handler** 映射表。
2. 顺带反 `constructor`/`initialize`/`0x44ad20`(子初始化)/`on_draw`(0x44b530,看它怎么按态选 `on_draw__*`)。
3. 产出:**状态机图**(态枚举 ↔ do_handler ↔ on_draw_handler ↔ 转移条件)。这是后续一切的脚手架。

### Phase 2 — 复用菜单控件(高 xref 待挖 = zMenuHelper 方法)
- 优先 `0x4560b0`(x7)、`0x4569a0`(x4)、`0x44dc70`(x4)、`0x44ec60`(x4)、`0x452c30`(x3)、`0x44c8c0`(x3)、`0x455370`(x3)。
- 判据(**中立、不喂标签**):看它是否操作 `zMenuHelper` 的 `current_selection/num_choices/stack_*`、
  是否读输入(按键状态全局)、是否驱动条目 anm。坐实后命名(move_cursor / push_submenu / pop_submenu /
  clamp_selection / draw_item_list 之类),**名落到具体读写偏移**。
- 命名这批后,所有 `do_*` 的可读性会大幅提升 → 再回头看 do_* 就快。

### Phase 3 — 逐菜单态深挖(大函数 + 相邻待挖)
- 按价值排:**character_select / subseason_select(★ SHT 选择链)** → options(`0x44c8c0` 明细)→
  key_config(`0x44ec60`)→ replay/music_room。
- 每态:do_handler + 它调用的待挖 helper + on_draw + 它写的 `zMainMenu`/存档字段,串成一条
  "输入 → 选择 → 转移/确认 → 写全局/存档" 链。
- ★ character/subseason:**反到它把选择写进哪个全局/存档字段,再追该字段被谁读去加载 `.sht`** —— 这是回扣 SHT 的关键。

### Phase 4 — 交叉印证 + 回流
- 与 ExpHP `funcs.json`/`type-structs` 逐项对名;**冲突先怀疑自己**(四闸门,memory `re-overclaim-guard`)。
- 存档/配置字段与 `statics.json`、配置结构体核对。
- 写 findings(见 §产出);命名 + 结构体经 `apply_th16_mainmenu_names.py` 固化;稳定结论回填 `../../docs/`。

## 4. 方法 / 纪律(每条结论必守)
- **五段证据链**:发现→推测→验证→结论(可信度+版本)→证据(地址/读写点)。一手反编译 > 推断 > 社区单源。
- **可信度** ✅一手实证 / 🟡单源或推断 / ❓存疑;**结论必注 "TH16 v1.00a"**。
- **防过拟合**:派子 agent 命名给**中立判据、不喂 ExpHP 标签**(memory `re-agent-no-hypothesis-priming`)。
- **机械活写脚本、勿派 agent**;扇出 ghidra 子 agent 极贵(memory `re-workflow-fanout-cost`):≤10/批、命名用 sonnet、先 inline 锚定。
- **二手 label 不算数**:ExpHP 字段名是导航,用途要自己反到读写点坐实(memory `re-evidence-chain-discipline`)。
- 落盘:函数名/注释走 MCP `rename_function`+`save_database`;结构体/数据符号走 driver 脚本 + `proj.save()`(memory `ghidra-mcp-save-broken`)。
- 重生成 worklist 前先 MCP `close_database` 释放锁(见 `README.md`)。

## 5. 计划产出
- `funcs/mainmenu/01-state-machine.md` —— on_tick 状态机图 + current_menu 枚举 → handler 映射(Phase 1)。
- `funcs/mainmenu/02-menu-helpers.md` —— zMenuHelper 控件方法语义(Phase 2)。
- `funcs/mainmenu/03-states-and-sht-selection.md` —— 各菜单态 + ★ character/subseason→SHT 选择链(Phase 3)。
- `../sht/disasm/scripts/apply_th16_mainmenu_names.py` —— 函数/结构体/注释,headless 可复现。
- 稳定后回填 `../../docs/`(SHT 选择链部分)。
  > (findings 暂放 `funcs/mainmenu/`;若 MainMenu 研究做大,可比照 `anm/`/`bullets/` 升格为顶层 `mainmenu/` 文件夹。)

## 6. 第一刀(下次动手起点)
**反 `MainMenu__on_tick`(0x44af80)** → 证实/证伪 "switch on `this+0x18 current_menu`" → 产出态枚举→handler 映射(Phase 1.1)。
同时跑 Phase 0 把 `zMainMenu`/`zMenuHelper` 套上 this,让 on_tick 的字段访问直接显字段名。
