# TH16 角色/副季选择 → .sht 加载链(Phase 3,★ SHT 回扣)

> 版本:**TH16 v1.00a**(`th16.exe`,imagebase 0x400000)。计划 `../mainmenu-plan.md`,前篇 01/02。
> 写于 2026-06-10,一手反编译 + xref 追踪。**这是把主菜单接回 SHT 任务的关键一篇。**

## 结论速览(✅ 一手)
主菜单的**角色选择**(state 6)和**副季选择**(state 7)把玩家选择写进一组全局配置变量,
开局时 **`player_shot_init`(0x440fb0)读这组全局,从 4 张字符串指针表选出对应的 `.sht`/`.anm` 文件,
经 `sht_parse_resolve_funcptrs` 解析 SHT、把 shot 行为函数指针装进 player 对象**。

完整链:`do_character_select`/`do_subseason_select` → `DAT_004a57a4`/`DAT_004a57ac` 等全局 → `player_shot_init` → `.sht` 表 + `sht_parse_resolve_funcptrs` → `player+0x2c788/0x2c78c` 行为 funcptrs。

---

## 1. 选择写入点(一手,来自 do_*_select 反编译)

### `MainMenu__do_character_select`(0x4502c0,state 6)
光标选择存 `this+0x24`(角色 index 0..3)。确认链:case 2 检测确认键(`DAT_004a50bc & 0x80001`)→ 进 case 3 →
计时满后 `LAB_004509e1`:
```c
MainMenu__change_menu(param_1, 7);              // → 进副季选择
DAT_004a57a4 = *(int*)(param_1 + 0x24);         // ★ 写【角色】选择
DAT_004a6f24 = DAT_004a57a4;                     //   镜像(开局参数块)
// 同时压入选择历史栈 +0x30[stack]/+0x70[stack],stack_index(+0xb0)++
```
取消(`& 0x102`)→ 退回上一态。

### `MainMenu__do_subseason_select`(0x450af0,state 7)
光标选择存 `this+0x24`(副季 index)。case 0 初始化时 `... + (short)DAT_004a57a4 + 0x1f` → **读角色选择**挑 anm。
确认链:case 2(`& 0x80001`)→ case 3 → 计时满(`+0x2b0 > 0x27`):
```c
DAT_004a57ac = *(int*)(param_1 + 0x24);   // ★ 写【副季】选择 (DAT_004a57b4==4 即 Extra 时强制 =4)
DAT_004a57c8 = 0xffffffff;
MainMenu__change_menu(param_1, 2);          // → state 2 = 开局淡出/进游戏转场
// 据 DAT_004a57b4(模式)设 DAT_004a6f18 / DAT_004a5790 / DAT_004c17c4(关卡/ECL 起点数据)
```
取消(case 4)→ 回角色选择(state 6),仍 `DAT_004a57ac = +0x24`。

### 全局配置块(开局参数,一手 + on_tick boot 旁证)
| 全局 | 含义 | 写处 | 读处(关键) |
| --- | --- | --- | --- |
| **`DAT_004a57a4`** | **角色(自机/shot type)选择** | do_character_select(0x4509ed) | `player_shot_init`、GameThread、ECL global、Spellcard、Gui… |
| `DAT_004a57a8` | 主 shot 表**基偏移**(正常 0;由 replay/+0x88 设) | on_tick boot | `player_shot_init`(`a57a8 + a57a4` 索引) 🟡 |
| **`DAT_004a57ac`** | **副季(sub weapon)选择** | do_subseason_select(0x450d95…) | `player_shot_init`、Item__init…season |
| `DAT_004a57b4` | 模式标志(`==4` = Extra/特殊;`>3` 分支) | on_tick boot(replay/+0x8c) | 两 do_select 顶部 `(==4)*2+0x96/0x97` |
| `DAT_004a6f24` | 角色选择镜像 | do_character_select | |
> on_tick 的 boot 态(case 0)从 replay 头 `uVar4+0x84/0x88/0x9c/0x8c` 填这组 → 回放时用录像里的选择;正常游戏用菜单写入。

## 2. 消费者 `player_shot_init`(0x440fb0,✅ 一手 + 旧 audit 旁证)
> 已有注释:"Resolves main(+0x2c788)+sub(+0x2c78c) .sht via sht_parse_resolve_funcptrs … Caller: player ctor 0x441c60. CONFIRMED(audit)." 本篇把它接到菜单选择源头。

按选择从 **4 张并行字符串指针表**取文件名(下标全来自菜单全局):
| 表 @地址 | 内容 | 下标 |
| --- | --- | --- |
| `PTR_s_pl00_sht_00492ca8` | **主 shot `.sht`**(`pl00.sht`…) | `DAT_004a57a8 + DAT_004a57a4`(角色) |
| `PTR_s_pl00sub_sht_00492cb8` | **副 `.sht`**(`pl00sub.sht`…) | `DAT_004a57ac`(副季) |
| `PTR_s_pl00_anm_00492ccc` | 主 `.anm` | `DAT_004a57a8 + DAT_004a57a4` |
| `PTR_s_pl00sub_anm_00492cdc` | 副 `.anm` | `DAT_004a57ac` |

核心(一手):
```c
// 预载贴图
player+0xc = AnmManager__preload_anm(9,  PTR_s_pl00_anm_00492ccc[a57a8 + a57a4]);
player+0x10= AnmManager__preload_anm(0x1e,PTR_s_pl00sub_anm_00492cdc[a57ac]);
// 解析 SHT(除非有缓存 DAT_004a6f00/efc,回放/重开走缓存)
sht_parse_resolve_funcptrs(player+0x2c788, PTR_s_pl00_sht_00492ca8[a57a8 + a57a4]);  // 主
sht_parse_resolve_funcptrs(player+0x2c78c, PTR_s_pl00sub_sht_00492cb8[a57ac]);       // 副
// 注册 shot on_tick(0x443720)/on_draw(0x443730);按角色 a57a4 设移动速度
//   (&DAT_00492c98/c88/c78 + a57a4*4 = 各角色低速/高速移动 float),初始化判定/季节等级等
```
解析结果落 `player+0x2c788`(主 shot 行为)/`+0x2c78c`(副)= **SHT 的 func_* 运行时函数指针** —— 即原 SHT 任务里"func_on_init/tick/draw/hit"被解析成的实际指针。

## 3. 这对 IDE / 原 SHT 任务意味着什么
- **菜单选择 → 文件**:角色 → `PTR_s_pl00_sht_00492ca8[a57a8+a57a4]`,副季 → `PTR_s_pl00sub_sht_00492cb8[a57ac]`。
  → 想知道"选某角色/副季实际加载哪个 .sht",读这两张表即可(下次可 dump 表内字符串确认 `pl0X.sht`/`pl0Xsub.sht` 命名)。
- **.sht 语义入口**:`sht_parse_resolve_funcptrs` 是把 SHT 字节(func_* 索引)解析为函数指针的解析器 —— 原 SHT 任务要的"func_* → 行为"就落在它+其装进的 `player+0x2c788/+0x2c78c`。**这是 SHT 运行时语义的正门**,后续解 func_* 应从这里顺藤摸瓜(它如何把 SHT 里的索引映射到具体 shot 行为函数)。
- 主/副分离:TH16 玩家 shot = **主 shot(角色)+ 副武器(副季)** 两套独立 .sht,分别解析、分别存指针。

## 4. 可信度 / 开放
- ✅ 选择写入点、全局名、player_shot_init 的表索引与 sht 解析调用:均一手反编译可见。
- 🟡 `DAT_004a57a8`(基偏移)正常值与来源未完全坐实(疑回放/特殊模式偏移);`DAT_004a57b4==4` 解为 Extra 是常识推断。
- ❓ 4 张表的具体字符串内容未 dump(符号名强烈暗示 `pl00*.sht/anm`);下次可读 PE 或反编译确认逐角色文件名。
- ▶ **顺藤目标(交给 SHT 主线)**:深挖 `sht_parse_resolve_funcptrs` 如何解析 func_* 索引 → 这是原 SHT 任务"func_* 运行时语义"的直接入口(本篇只接到门口)。

## 落盘
- 本篇纯追踪,无新 rename(player_shot_init / sht_parse_resolve_funcptrs 已命名)。
- 全局配置块 `DAT_004a57a4/a8/ac/b4`、4 张表符号 → 建议在 `apply_th16_mainmenu_names.py` 里给数据符号改名 + 注释(数据符号须 driver 脚本落盘,见 memory `ghidra-mcp-save-broken`)。
- 稳定后回填 `../../docs/`(SHT 选择/加载链)。
