# th18.v1.00a 未挖函数地图(给新会话的任务指导)

> **版本**：TH18 v1.00A（`th18.exe`，imagebase `0x400000`）。本文裸地址默认属该版本；引用其他版本须写成 `th16:0x…`。
> 自动生成:`tooling/ghidra/build_worklist.py th18`(交叉当前工程快照 × ExpHP th-re-data)。
> 重生成:`python tooling/ghidra/build_worklist.py th18`。本表 = th18.v1.00a。

## 总览
| 类别 | 数量 | 含义 |
| --- | --- | --- |
| 总函数 | 2333 | 工程内全部 |
| ✅ 已命名(我们/研究) | 974 | 我们反过/命名过(非 FUN_、非 CRT) |
| 📥 可从 ExpHP 导入 | 0 | 我们还是 FUN_,但 ExpHP 已命名 → 批量导名即得 |
| 🔬 真·待挖 | 963 | 我们和 ExpHP 都没命名(非 CRT)= 研究处女地 |
| ⚙️ CRT/库/thunk | 396 | 编译器运行时,非研究目标 |

## 📥 可从 ExpHP 导入(低垂果实:先批量导名,白得上下文)
> 这些 ExpHP 已命名、我们工程里还是 `FUN_`。建议先写脚本批量 import(参考 `apply_th16_ecl_names.py` + ExpHP funcs.json),
> 立刻把 ~0 个函数变可读,再在其上做语义。按子系统分布:

| 子系统(ExpHP 前缀) | 待导入数 |
| --- | --- |

## 🔬 真·待挖函数(谁都没命名,按大小排;大小=字节数,xrefs=被引用数,hint=最近的已命名邻居→子系统线索)
> 这是真正的研究处女地。优先挖**大 + 高 xrefs + hint 指向你关心的子系统**的。⚠️ 个别可能是 Ghidra 没认出的 CRT,反编译时自行判断。

| addr | size | xrefs | 子系统线索(nearest named) |
| --- | --- | --- | --- |
| `0x00430d30` | 22274 | 1 | EnemyData |
| `0x00458e40` | 5615 | 1 | ScoreFileShotData |
| `0x004a3015` | 4937 | 3 | _memset |
| `0x0042be70` | 3154 | 1 | Ending |
| `0x00424fe0` | 2809 | 1 | BulletManager |
| `0x0043a8b0` | 2711 | 2 | GuiMsgVm |
| `0x0043cd00` | 2536 | 1 | Gui |
| `0x0047dce0` | 2532 | 9 | AnmManager |
| `0x00476d20` | 2473 | 6 | SoundManager |
| `0x0047f530` | 2405 | 1 | AnmManager |
| `0x00480160` | 2258 | 2 | AnmManager |
| `0x0047bef0` | 2098 | 1 | AnmVm |
| `0x00461e90` | 2032 | 2 | ReplayManager |
| `0x00485110` | 1985 | 1 | AnmManager |
| `0x004858e0` | 1953 | 3 | AnmManager |
| `0x00404440` | 1763 | 1 | PosVel |
| `0x0045fc80` | 1696 | 1 | enm_compute_damage_sources |
| `0x00460320` | 1657 | 1 | enm_compute_damage_sources |
| `0x0042e5a0` | 1626 | 1 | Enemy |
| `0x0041efa0` | 1580 | 1 | StageInner |
| `0x00402fb0` | 1575 | 10 | PosVel |
| `0x00436cf0` | 1568 | 1 | EnemyData |
| `0x0042f890` | 1515 | 1 | EnemyData |
| `0x00468130` | 1446 | 1 | MainMenu |
| `0x00406d00` | 1428 | 1 | Timer |
| `0x004704c0` | 1397 | 1 | TrophyNotice |
| `0x00443e60` | 1374 | 1 | GameThread |
| `0x004aadde` | 1334 | 1 | _memset |
| `0x00490e00` | 1330 | 5 | _memset |
| `0x004914c0` | 1330 | 33 | _memset |
| `0x004a94d0` | 1311 | 1 | _memset |
| `0x00427f40` | 1307 | 1 | Bullet |
| `0x00428970` | 1306 | 1 | Bullet |
| `0x00480a50` | 1302 | 2 | AnmManager |
| `0x00470a40` | 1259 | 3 | TrophyNotice |
| `0x004432c0` | 1253 | 2 | GameThread |
| `0x0047f090` | 1174 | 2 | AnmManager |
| `0x00474850` | 1151 | 1 | Window |
| `0x0044fb10` | 1136 | 6 | LaserCurve |
| `0x00439a10` | 1128 | 2 | EnemyData |
| `0x0047e8f0` | 1120 | 6 | AnmManager |
| `0x00441a50` | 1115 | 1 | GuiMsgVm |
| `0x0042a320` | 1110 | 1 | Bomb |
| `0x0041ca90` | 1093 | 1 | Stage |
| `0x00454b20` | 1059 | 1 | wait_for_game_thread |
| `0x00482170` | 1046 | 1 | AnmManager |
| `0x00486bc0` | 1018 | 1 | AnmManager |
| `0x0046ac00` | 1007 | 1 | MainMenu |
| `0x00458090` | 992 | 1 | ScoreFileShotData |
| `0x00481d90` | 981 | 3 | AnmManager |
| `0x00404080` | 959 | 3 | PosVel |
| `0x0044ff80` | 954 | 2 | LaserCurve |
| `0x004698c0` | 954 | 1 | MainMenu |
| `0x0048fde7` | 949 | 1 | _memset |
| `0x004078d0` | 946 | 1 | AnmManager |
| `0x004734e0` | 937 | 2 | Window |
| `0x00472280` | 923 | 1 | WinMain |
| `0x00476410` | 908 | 1 | ScreenEffect |
| `0x00455610` | 905 | 1 | Supervisor |
| `0x00470010` | 902 | 1 | TrophyNotice |

(共 963 个真·待挖;上表为最大的 60 个。全量在 `local/th18.v1.00a/th18-funcs.json` 自行筛 name 以 FUN_ 开头者。)

## 🔬 待挖函数按子系统线索聚合(挑一片整体挖)
| 子系统线索 | 待挖数 | 累计字节 |
| --- | --- | --- |
| AnmManager | 88 | 40678 |
| EnemyData | 50 | 33130 |
| _memset | 171 | 30576 |
| Window | 31 | 12712 |
| ScoreFileShotData | 14 | 10903 |
| TrophyNotice | 47 | 10620 |
| GuiMsgVm | 15 | 8597 |
| PosVel | 17 | 8097 |
| Bullet | 12 | 7874 |
| Supervisor | 29 | 7823 |
| MainMenu | 14 | 7613 |
| AnmVm | 30 | 7198 |
| enm_compute_damage_sources | 17 | 7005 |
| ReplayManager | 13 | 6472 |
| Timer | 22 | 5987 |
| Enemy | 55 | 4621 |
| BulletManager | 17 | 4296 |
| UpdateFunc | 13 | 3890 |
| Ending | 4 | 3752 |
| GameThread | 7 | 3688 |
| SoundManager | 5 | 3474 |
| Player | 15 | 3076 |
| Gui | 9 | 2937 |
| AbilityManager | 12 | 2892 |
| AnmLoaded | 27 | 2516 |
