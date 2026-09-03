# assets/ability — `ability.anm` 追加（卡牌场上特效）

> **版本**：TH18 v1.00a（`th18.exe`，imagebase `0x400000`）。本文裸地址默认属该版本；引用其他版本须写成 `th16:0x…`。

`ability.anm` 是主动卡场上特效的家（零售 7 张贴图 / 68 个脚本，Tenshi 的要石是 script28）。
脚本只能用同文件里的 sprite，所以要在特效里露出卡图，就把卡图**副本**追加成一个 entry。

| 放什么 | 在哪 | 规则 |
| --- | --- | --- |
| 贴图 | `entries/ORDER.txt`：`NAME  源图(相对 assets/)` | 源图 256×320；只追加不重排。第 k 行 → entry 7+k / sprite 109+k（由零售文件算出） |
| 脚本 | `scripts/NN_name.anm.txt`，`NN` 从 68 起连续 | 一个文件一个 `script scriptNN { … }`；正文用 `@NAME` 引用上面的 sprite |

`make anm` 跑 `build_ability.py`：重编 → `native/build/ability.anm`，自检零售部分没变，
并生成 `native/anm_ids.h`（`CE_ANM_ABILITY_SPRITE_<NAME>` / `CE_ANM_ABILITY_SCRIPT_<name>`），C 里用它起脚本：

```c
ce_anm_spawn(CE_ABILITY_ANM(), CE_ANM_ABILITY_SCRIPT_REVERSE_FLASH, 16);   /* 场地中央 */
```

写脚本参照 `local/th18.v1.00a/anm/ability/ability.anm.txt` 里的零售脚本和 thpages 的指令表；
`type(8)` 是三维渲染模式，`rotateTime(t, mode, rx, ry, rz)` 绕 Y 轴转就是翻牌。
`originMode(1)` + 实体坐标 (0,0,0) = 场地正中。
