# TH16 MainMenu 状态机骨架(Phase 1)

> 版本:**TH16 v1.00a**(`th16.exe`,imagebase `0x400000`)。
> 计划:`../mainmenu-plan.md`。本篇 = Phase 1 产出(on_tick 分派 + 转移函数 + 状态枚举)。
> 写于 2026-06-10,一手反编译。可信度见各条。

## 结论速览
- ✅ **`MainMenu__on_tick`(0x44af80)是状态机分派器**,`switch (this->current_menu)`,即 `switch(*(int*)(this+0x18))`。
- ✅ **`zMainMenu` 前部布局一手坐实**:`+0x18 current_menu` · `+0x1c previous_menu` · `+0x20 status`(态内子相位)· `+0x2ac time_on_current_menu`(zTimer)。与 ExpHP `type-structs-own.json` 完全一致。
- ✅ **`MainMenu__change_menu(this, new)`**(原 `FUN_0044a560`,已命名):菜单态转移的唯一 setter。
- ✅ **状态枚举 0x00–0x14 → handler 全表**(见下)。
- ✅ 新命名 **`MainMenu__do_help_manual`**(原 `FUN_004545a0`,state 0x10):操作说明/HelpManual 屏。

---

## 1. 分派器 `MainMenu__on_tick` @ 0x44af80
**发现**:函数签名 `__fastcall MainMenu__on_tick(uint *this)`,核心是 `switch(this[6])`(`this[6]` = 字节偏移 `0x18`)。
**验证**:`this` 为 `uint*`,索引 6 = `0x18`;与 `zMainMenu+0x18 current_menu` 对齐;`change_menu` 写的也是 `+0x18`(见 §2)→ 互证。
**结论(✅,TH16 v1.00a)**:on_tick 每帧按 `current_menu` 分派到对应 `do_*`。证据:0x44af80 的 `switchD_0044b16d`。

附带:
- 函数头部处理 **demo/attract 计时**(`DAT_004a5bf0` 计到 `0x708`=1800 帧→自动放 demo 录像,经 `ReplayManager__destructor`/`ecl_free_runcontext`)与 **BGM/标题进入**(`param_1[0x173a]` 标志 + `SoundManager__modify_bgm` + `FUN_0043c370(0,"th16_01")` 加载标题曲)。🟡 细节未逐一坐实,大意明确。
- 尾部 `param_1[0xab..0xae]` + `PTR_DAT_00490eb0[param_1[0xae]]` = 某周期性 float 推进(疑菜单背景/光标动画时基)。🟡 待 Phase 2/3 复核。

## 2. 转移函数 `MainMenu__change_menu` @ 0x44a560(原 FUN_0044a560)
**发现/证据**(一手反编译):
```c
this->previous_menu = this->current_menu;   // +0x1c = +0x18
this->current_menu  = new_menu;             // +0x18 = arg
this->status        = 0;                     // +0x20 = 0   (态内子相位归零)
// 首次:置 this+0x2bc bit0,初始化 +0x2ac/+0x2b0/.. 计时块(0xfff0bdc1 哨兵)
this->time_on_current_menu = 0xffffffff;     // +0x2ac (zTimer 复位)
```
**结论(✅,TH16 v1.00a)**:菜单态切换的唯一入口;同时复位 `status` 与 `time_on_current_menu`。
→ **`status`(+0x20)= 每个 `do_*` 内部的"进入/激活/退出"子相位计数**(do_* 普遍 `switch/if (status)`,见 help_manual 实例 §4)。

## 3. 状态枚举 → handler 全表(✅ 一手,来自 on_tick switch)
| current_menu | handler | 说明 |
| --- | --- | --- |
| 0x00 | (内联 boot/transition) | 开机/返回菜单的转场:据全局 `DAT_004a6f1c`(返回目标)决定去哪个态;禁用残留 anm VM;`change_menu` 到目标 |
| 0x01 | `MainMenu__do_title_screen` | 标题主菜单 |
| 0x02 | (内联→ fall through 9/0xc) | 设 `DAT_004c17c4` 后并入 0x09/0x0c |
| 0x03 | `MainMenu__do_options` | 选项 |
| 0x04 | `MainMenu__do_key_config` | 键位配置 |
| 0x05 | `MainMenu__do_difficulty_select` | 难度选择 |
| 0x06 | `MainMenu__do_character_select` | ★ 角色(自机)选择 → 决定 .sht |
| 0x07 | `MainMenu__do_subseason_select` | ★ 副季选择 → 决定 .sht 槽 |
| 0x08 | `MainMenu__do_practice_stage_select` | 练习关卡选择 |
| 0x09 / 0x0c | `FUN_0043c440`(共用) | 转场/淡出(待命名;非 MainMenu 前缀) |
| 0x0a | `MainMenu__sub_452330_replay_related` | 录像相关 |
| 0x0b | `MainMenu__do_replay_menu` | 录像菜单 |
| 0x0d | `MainMenu__do_music_room` | 音乐室 |
| 0x0e | `MainMenu__do_menu_sub_4532f0` | (子菜单,待定语义) |
| 0x0f | `MainMenu__sub_453c10_replay_replated` | 录像相关 |
| 0x10 | **`MainMenu__do_help_manual`** | ✅ 操作说明屏(HelpManual,本篇新命名) |
| 0x11 | `MainMenu__do_spell_practice_stage_select` | 符卡练习-关卡 |
| 0x12 | `MainMenu__do_spell_practice__spellcard` | 符卡练习-符卡 |
| 0x13 | `MainMenu__do_spell_practice__difficulty` | 符卡练习-难度 |
| 0x14 | `MainMenu__do_spell_practice__subseason` | 符卡练习-副季 |

> 🟡 注:`do_difficulty/character/subseason_select` 等名为 ExpHP 导入,**语义待 Phase 3 一手坐实**;但其在 switch 中的**状态号**是一手确定的。

## 4. 实例:`MainMenu__do_help_manual` @ 0x4545a0(state 0x10,本篇新命名)
**发现/证据**:`switch (status @ +0x20)`:`status==0` → 建两个 anm 特效 + `HelpManual__operator_new()`,置 `status=1`、复位 timer;`status==1` 且某全局条件成立 → `AnmManager__interrupt_tree` 收两个 anm、`HelpManual__destructor`+`ecl_free_runcontext`、`change_menu(this,1)` 回标题。
**结论(✅,TH16 v1.00a)**:state 0x10 = 操作说明/HelpManual 屏。**也佐证了 `status`(+0x20)是态内子相位**(0=入场建对象,1=激活/等退出)。

## 待命名(本篇顺带定位,留给 Phase 2/3)
- `FUN_0043c440`(state 9/0xc 共用转场)、`FUN_0043c370(0,"th16_01")`(加载标题 BGM/资源)、`FUN_0043c3f0`、`FUN_0041a360`、`FUN_00418720`、`FUN_00402de0`、`Globals__leaf_449190`。
- 全局:`DAT_004a6f1c`(返回菜单目标)、`DAT_004a5bf0`(demo 计时)、`DAT_004c0f48`(AnmManager,已知)。

## 落盘
- 已 MCP `rename_function`:`MainMenu__change_menu`(0x44a560)、`MainMenu__do_help_manual`(0x4545a0)。函数名跨会话可靠落盘。
- 结构体类型套用 + 注释 → 待 Phase 0 脚本 `apply_th16_mainmenu_names.py`(driver + proj.save)。
