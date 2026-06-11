# 给 ExpHP th-re-data 提 PR 的准备清单(TH16 MainMenu)

> 目标仓库:`github.com/exphp-share/th-re-data`(vendor 克隆在 `../../ecl/vendor/th-re-data`,gitignore)。
> 版本目录:`data/th16.v1.00a/`。本会话成果对照他们的贡献规则整理。写于 2026-06-10。

## 他们的规则(README "Contributing")
- ✅ **可 PR**:`funcs.json`、`statics.json`(函数/静态符号名+注释)。
- ❌ **不可 PR**:`type-structs-*.json`(他无法 import 改动)→ struct 字段走 **issue + C 定义**(未知区用 `char[]` 占位)。
- ⚙️ 别碰:`type-structs-ext`/`type-aliases`/`type-enums`/`labels.json`(binja 自动生成)。

## 格式硬要求(否则 diff 爆炸)
- `funcs.json` 是 **CRLF** 换行,首行空行再 `[ {…}`,其后每条**行首 `, `**,对象 compact 单行。键序 `addr,name,comment`。
- 地址**小写去前导零**(`0x44a560`),**按地址升序**插入。名用 **`::`**(类),子部分用 `method__sub`。

---

## A. funcs.json —— 16 个新函数(逐条承重依据)
> 依据标注:`[ExpHP名]`=踩在他已命名的 callee/全局上(可信);`[硬]`=字符串/算术/API/控制流(标签无关);`[ours]`=我们解读 ExpHP 未标处(已钉到写入点)。

| addr | PR 名(`::`) | 承重依据 |
| --- | --- | --- |
| 0x44a560 | `MainMenu::change_menu` | [硬] 写 +0x18/+0x1c/+0x20 一手 |
| 0x44ad20 | `MainMenu::destructor` | [硬:RTTI] 入口写 `TitleInf::vftable`(PE 含 `.?AVTitleInf@@`);[ExpHP名] ReplayManager__destructor / UpdateFuncRegistry__unregister |
| 0x44af50 | `MainMenu::delete_singleton` | [硬] 3 行:调 destructor + ecl_free_runcontext + 清全局 |
| 0x4545a0 | `MainMenu::do_help_manual` | [ExpHP名] HelpManual__operator_new / __destructor |
| 0x44c8c0 | `MainMenu::do_options__update_sprites` | [ExpHP名] AnmVm__run/AnmManager;[硬] 3 caller 全在 do_options、无状态写 |
| 0x44dc70 | `MainMenu::draw_option_volume_digits` | [硬] `"SetVol"` + 拆位算术;[ExpHP名] SoundManager__modify_bgm |
| 0x44ec60 | `MainMenu::draw_key_config_digits` | [硬] 两位数拆位算术;[ExpHP名] AnmLoaded__set_sprite |
| 0x44f710 | `MainMenu::key_config_swap_key` | [硬] swap 逻辑 + play_sound_centered(7);caller 按键检测 |
| 0x44f810 | `MainMenu::refresh_key_config_row_anm` | [硬] interrupt 0x1e/0x1f 控制流;[ExpHP名] AnmVm__run |
| 0x451560 | `MainMenu::load_replay_files_thread` | [硬] `FindFirstFileA("th16_ud????.rpy")` + `"th16_%.2d.rpy"`;[ExpHP名] ReplayManager__read_replay_file ←**替换他的占位** `sub_451560_start_of_a_thread__rpy_related`(correction) |
| 0x452c30 | `MainMenu::draw_spellcard_score_rows` | [硬] 读 SCOREFILE 每符记录(名 +0x15538/尝试 +0x155c0,stride 0x9c)、按难度 `DAT_00491700[i]` 过滤、`"No.%s%s%s %s %4d/%4d"`(捕获/尝试)←**原名"replay"已纠为"spellcard score"** |
| 0x4560b0 | `MainMenu::spell_practice_update_spellcard_list` | [硬] 格式串 `"No.%3d  %s"` + 构建 +0x5dd0 数组;[ExpHP名] AnmLoaded__create_effect |
| 0x4569a0 | `MainMenu::spell_practice_update_selection_anm` | [硬] 5 次循环 interrupt 2/3;[ExpHP名] AnmManager__interrupt_tree |
| 0x456060 | `MainMenu::spell_practice_is_accessible` | [ours] +0x155c0 写入点(`ecl_spell_417f00` `+1`)=尝试计数;caller 用返回值 gate(返 0 播错误音) |
| 0x455330 | `text_skip_line` | [硬] 纯 char 扫描,零标签依赖 |
| 0x455370 | `text_read_line_into_buf` | [硬] 纯 char 复制,零标签依赖 |

> 注:0x44a560 是 MainMenu 方法但地址在 constructor(0x44a9f0)之前;PR 时按 0x44a560 升序位置插入。

## B. statics.json —— 2 张已坐实的表(在真·未命名静态内存)
| addr | PR 名 | type | 依据 |
| --- | --- | --- | --- |
| 0x490ee0 | `SPELL_PRACTICE_TABLE` | (建议 `int32[5]` per entry / 或注释为 spell-id 列表 +`-1` 终止) | [硬] PE 字节:`[0,1,2,3,-1]…`,索引 `(route*0xd+sec)*0x14`,终止符对上代码 |
| 0x491700 | `SPELL_DIFFICULTY_BY_ID` | `uint8_t[0x77]` | [硬] `DIFFICULTY(0x4a57b4)=DAT_00491700[id]`;值域 {0–4}=E/N/H/L/Extra;119 项 |

> **不要提**:`CHARACTER 0x4a57a4`、`SUBSEASON 0x4a57ac`、`SUBSHOT__ZERO_IN_TH16 0x4a57a8`、`DIFFICULTY 0x4a57b4`、
> `SCOREFILE_PTR 0x4a6f0c`、`CACHED_PLAYER_SHT_FILE 0x4a6f00`、4 张 `*_SHT/ANM_FILENAMES`(0x492ca8/cb8/ccc/cdc)
> —— 这些 **ExpHP statics.json 已有**(我们 Phase 3 独立反编译与之逐项吻合 = 强交叉验证)。

## C. 走 issue(struct/字段,不能 PR)—— 附 C 定义 + `char[]` 占位
- **`zMainMenu` 真名 = `TitleInf`**(内嵌 `ThreadInf`):dtor 入口 `*this=TitleInf::vftable`、尾 `+0x5de4 = ThreadInf::vftable`。**证据=RTTI**:PE 含 `.?AVTitleInf@@`/`.?AVThreadInf@@`,`MainMenu` 0 次。
  → ★ 可单独开一个高价值 issue:**TH16 保留完整 MSVC RTTI**,ZUN 全部多态类真名可从 `.?AV*Inf@@` 还原(EnemyInf/BombInf/LaserBeamInf…),可系统校正 ExpHP 的类命名层。
- `zConfig +0x26`(=`SUPERVISOR.config+0x26`,现 `__unknown`)= BGM/SE 音量字节([硬] `"SetVol"`+拆位)。
- `zScorefile`(现仅 base+size,无内部字段):`+0x155c0` 起按符卡 stride `0x9c` 的记录,首 int = **尝试计数**([硬] `ecl_spell_417f00` `+1`)。
- `zMainMenu` 的 `__unknown` 区字段(行为已证,用途带结构推断,措辞保守):
  `+0x5b34 short[6]` 键位码 · `+0x740` 符卡条目 anm 数组 · `+0x5b50` 录像指针表[100] · `+0x5ce8` 录像加载标志位(bit2 中止/bit3 完成) · `+0x5dd0` 当前符卡选择数组。

## D. provenance / 诚实声明(写进 PR 正文)
- 来源:独立 Ghidra 反编译 TH16 v1.00a,菜单子系统;经第二批子 agent 对抗式复核(0 假阳性,3 处收紧措辞)。
- A 类多数踩 ExpHP 已命名锚点或字符串/算术硬证据;**唯一 `[ours]` 项**(spell_practice_is_accessible)的语义已钉到写入点,PR 里注明依据。
- 建议拆分:**PR#1 = funcs.json(16)**(最干净)→ **PR#2 = statics.json(2 表)** → **issue = struct/TitleInf**。
