# TH16 未挖函数地图(给新会话的任务指导)

> 自动生成:`funcs/build_worklist.py`(交叉 `funcs/th16-funcs.json` 当前工程快照 × ExpHP th-re-data)。
> 重生成:见 `funcs/README.md`。本表 = TH16 v1.00a。

## 总览
| 类别 | 数量 | 含义 |
| --- | --- | --- |
| 总函数 | 1764 | 工程内全部 |
| ✅ 已命名(我们/研究) | 888 | 我们反过/命名过(非 FUN_、非 CRT) |
| 📥 可从 ExpHP 导入 | 0 | 我们还是 FUN_,但 ExpHP 已命名 → 批量导名即得 |
| 🔬 真·待挖 | 499 | 我们和 ExpHP 都没命名(非 CRT)= 研究处女地 |
| ⚙️ CRT/库/thunk | 377 | 编译器运行时,非研究目标 |

## 📥 可从 ExpHP 导入(低垂果实:先批量导名,白得上下文)
> 这些 ExpHP 已命名、我们工程里还是 `FUN_`。建议先写脚本批量 import(参考 `apply_th16_ecl_names.py` + ExpHP funcs.json),
> 立刻把 ~0 个函数变可读,再在其上做语义。按子系统分布:

| 子系统(ExpHP 前缀) | 待导入数 |
| --- | --- |

## 🔬 真·待挖函数(谁都没命名,按大小排;大小=字节数,xrefs=被引用数,hint=最近的已命名邻居→子系统线索)
> 这是真正的研究处女地。优先挖**大 + 高 xrefs + hint 指向你关心的子系统**的。⚠️ 个别可能是 Ghidra 没认出的 CRT,反编译时自行判断。

| addr | size | xrefs | 子系统线索(nearest named) |
| --- | --- | --- | --- |
| 0x00481791 | 5019 | 3 | global_heap_set_null |
| 0x00408650 | 2128 | 1 | AsciiManager |
| 0x00448400 | 2061 | 2 | ReplayManager |
| 0x0046b900 | 1985 | 1 | AnmManager |
| 0x00405700 | 1973 | 1 | AnmVm |
| 0x0046c0d0 | 1964 | 3 | AnmManager |
| 0x00446870 | 1409 | 1 | PlayerBullet |
| 0x004895ce | 1334 | 1 | math_call_by_name_488bb0 |
| 0x00487af0 | 1311 | 2 | math_fmod |
| 0x00437ee0 | 1164 | 4 | LaserCurve |
| 0x00410550 | 1148 | 1 | BombSubWinter |
| 0x00438370 | 986 | 2 | LaserCurve |
| 0x00457b20 | 986 | 2 | Arcfile |
| 0x00404220 | 982 | 2 | collision_test_circle_rect |
| 0x00458730 | 954 | 1 | Arcfile |
| 0x00404600 | 947 | 1 | collision_test_circle_rect |
| 0x0042e150 | 880 | 2 | GameThread |
| 0x00468fc0 | 869 | 1 | AnmVm |
| 0x00403ec0 | 860 | 5 | collision_test_circle_rect |
| 0x00470320 | 856 | 1 | disabled_logger_470240 |
| 0x00468c70 | 843 | 3 | AnmVm |
| 0x00470680 | 809 | 1 | disabled_logger_470240 |
| 0x0043cb10 | 761 | 1 | Supervisor |
| 0x00488010 | 747 | 2 | math_fmod |
| 0x0046d3b0 | 734 | 1 | AnmLoaded |
| 0x0045d510 | 708 | 1 | SoundManager |
| 0x0045e990 | 702 | 1 | SoundManager |
| 0x00489b2e | 681 | 1 | math_call_by_name_488bb0 |
| 0x0045b7d0 | 673 | 1 | set_window_resolution_from_cfg |
| 0x0045b530 | 663 | 2 | set_window_resolution_from_cfg |
| 0x00403a90 | 661 | 1 | interp_common_methods |
| 0x0047a0e0 | 649 | 1 | create_thread_47952b |
| 0x00469e20 | 641 | 1 | cartesian_from_polar_469e00 |
| 0x0046a0b0 | 639 | 1 | cartesian_from_polar_469e00 |
| 0x00449a00 | 624 | 2 | scorefile_sub_449880 |
| 0x00487910 | 619 | 1 | memcpy_1 |
| 0x0043bbd0 | 618 | 1 | Supervisor |
| 0x0048511e | 614 | 1 | global_heap_set_null |
| 0x00407e00 | 609 | 2 | AsciiManager |
| 0x0045a450 | 609 | 1 | UpdateFuncRegistry |
| 0x00470bb0 | 605 | 2 | disabled_logger_470240 |
| 0x00488790 | 605 | 3 | _math_sqrt |
| 0x004714c0 | 597 | 1 | disabled_logger_470240 |
| 0x00469640 | 588 | 1 | AnmVm |
| 0x00443cd0 | 576 | 1 | kill_player_in_circle |
| 0x0046c920 | 572 | 1 | AnmManager |
| 0x0047fcb4 | 570 | 1 | wrap_CreateDirectory |
| 0x00469330 | 569 | 1 | AnmVm |
| 0x0048a17e | 564 | 1 | math_call_by_name_488bb0 |
| 0x00458130 | 561 | 1 | Arcfile |
| 0x00469bd0 | 558 | 1 | AnmVm |
| 0x0040c280 | 541 | 1 | ecl_callSTD_40c040 |
| 0x00427730 | 539 | 1 | gui_426d70_initializes_many_anms |
| 0x0043be40 | 528 | 1 | Supervisor |
| 0x0042b820 | 514 | 2 | GuiMsgVm |
| 0x0045b330 | 505 | 1 | set_window_resolution_from_cfg |
| 0x0047e540 | 486 | 1 | compat_RoUninitialize |
| 0x0046d1c0 | 485 | 1 | AnmLoaded |
| 0x0045dc50 | 472 | 1 | SoundManager |
| 0x00484070 | 470 | 1 | global_heap_set_null |

(共 499 个真·待挖;上表为最大的 60 个。全量在 `funcs/th16-funcs.json` 自行筛 name 以 FUN_ 开头者。)

## 🔬 待挖函数按子系统线索聚合(挑一片整体挖)
| 子系统线索 | 待挖数 | 累计字节 |
| --- | --- | --- |
| AnmVm | 21 | 8026 |
| global_heap_set_null | 31 | 7286 |
| Arcfile | 32 | 7281 |
| disabled_logger_470240 | 29 | 6797 |
| AnmManager | 13 | 6722 |
| Supervisor | 23 | 5170 |
| math_call_by_name_488bb0 | 20 | 4801 |
| SoundManager | 14 | 3752 |
| PlayerBullet | 10 | 3416 |
| ReplayManager | 7 | 2960 |
| AsciiManager | 4 | 2874 |
| collision_test_circle_rect | 3 | 2789 |
| PauseMenu | 13 | 2786 |
| AnmLoaded | 11 | 2481 |
| LaserCurve | 3 | 2292 |
| math_fmod | 2 | 2058 |
| BombSubWinter | 4 | 1967 |
| set_window_resolution_from_cfg | 3 | 1841 |
| compat_RoUninitialize | 14 | 1820 |
| global_heap_alloc_zeroed | 13 | 1727 |
| GuiMsgVm | 8 | 1680 |
| wrap_CreateDirectory | 11 | 1421 |
| TranslatorGuardHandler | 11 | 1347 |
| cartesian_from_polar_469e00 | 2 | 1280 |
| reads_file_into_new_allocation_402440 | 7 | 1128 |
