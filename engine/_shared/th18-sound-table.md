# th18 音效 id 表（`play_sound(id)` → `se_*.wav`）

> **版本**：TH18 v1.00a（`th18.exe`，imagebase `0x400000`）。本文裸地址默认属该版本；引用其他版本须写成 `th16:0x…`。
> 一手（2026-09-04，headless pyghidra + 直读 exe），为 card-expand 找 trophy 音效时顺带把整张表恢复出来。

## 0. 结论

- `SoundManager__play_sound_at_position(id)` `0x476c70`（stdcall(id) + xmm2 声像；`FUN_00476be0` 是两参版）：
  按 `id*0x14 + 0x4c9b8a` 取 word 优先级，把 id 排进 `0x56ad9c` 的 12 槽队列。
- 配置表 **`0x4c9b80`，0x52 项 × 0x14 字节**：`+0` 缓冲区号（0..0x51 的一个置换）、`+4` wav 指针表下标、`+8` 低 word 声像 / 高 word 音量、`+0x10` 标志。
- wav 指针表 **`0x4b47a0`，72 个 `char*`**（`se_*.wav`，`se_cardget` 出现两次）。
- 初始化 `FUN_00476410`：对每项 j，`buffer[f0[j]] ← 装载 ptr[f1[j]]`（`0x476716` `mov eax,[eax*4+0x4c9b84]`；`0x47671d` `push [eax*4+0x4b47a0]`）。
  所以 **`play_sound(id)` 放的是 j 满足 `f0[j] == id` 的 `ptr[f1[j]]`**。
- 验证（与既有一手结论互证）：`0x05` 敌机/boss 死亡 `enep01`、`0x07` 商店确认 `ok00`、`0x10` 买不起 `invalid`、`0x11` 加命 `extend`、
  `0x2c` X 键 bomb `slash`、`0x2e` 得 bomb `cardget`、`0x4d` Tenshi 发动 `release`、`0x4e` 切主动卡 `changeitem` —— 全部符合各处调用点的语义 ✅。

## 1. 表

| id | wav | 音量 |
| --- | --- | --- |
| `0x00` | `se_plst00.wav` | 0 |
| `0x01` | `se_plst00.wav` | 0 |
| `0x02` | `se_pldead00.wav` | 100 |
| `0x03` | `se_enep00.wav` | 5 |
| `0x04` | `se_enep00.wav` | 5 |
| `0x05` | `se_enep01.wav` | 100 |
| `0x06` | `se_enep02.wav` | 100 |
| `0x07` | `se_ok00.wav` | 100 |
| `0x08` | `se_ok00.wav` | 100 |
| `0x09` | `se_cancel00.wav` | 100 |
| `0x0a` | `se_select00.wav` | 10 |
| `0x0b` | `se_timeout.wav` | 100 |
| `0x0c` | `se_timeout2.wav` | 100 |
| `0x0d` | `se_powerup.wav` | 90 |
| `0x0e` | `se_pause.wav` | 100 |
| `0x0f` | `se_cardget.wav` | 100 |
| `0x10` | `se_invalid.wav` | 100 |
| `0x11` | `se_extend.wav` | 100 |
| `0x12` | `se_lazer00.wav` | 50 |
| `0x13` | `se_lazer01.wav` | 50 |
| `0x14` | `se_lazer02.wav` | 0 |
| `0x15` | `se_tan00.wav` | 50 |
| `0x16` | `se_tan01.wav` | 50 |
| `0x17` | `se_tan02.wav` | 50 |
| `0x18` | `se_tan00.wav` | 20 |
| `0x19` | `se_tan01.wav` | 20 |
| `0x1a` | `se_tan02.wav` | 20 |
| `0x1b` | `se_tan00.wav` | 50 |
| `0x1c` | `se_power0.wav` | 100 |
| `0x1d` | `se_power1.wav` | 100 |
| `0x1e` | `se_ch00.wav` | 100 |
| `0x1f` | `se_ch01.wav` | 100 |
| `0x20` | `se_gun00.wav` | 10 |
| `0x21` | `se_cat00.wav` | 100 |
| `0x22` | `se_damage00.wav` | 0 |
| `0x23` | `se_damage01.wav` | 0 |
| `0x24` | `se_nodamage.wav` | 0 |
| `0x25` | `se_item00.wav` | 0 |
| `0x26` | `se_kira00.wav` | 50 |
| `0x27` | `se_kira01.wav` | 50 |
| `0x28` | `se_kira02.wav` | 50 |
| `0x29` | `se_kira00.wav` | 50 |
| `0x2a` | `se_graze.wav` | 20 |
| `0x2b` | `se_graze.wav` | 20 |
| `0x2c` | `se_slash.wav` | 100 |
| `0x2d` | `se_slash.wav` | 100 |
| `0x2e` | `se_cardget.wav` | 100 |
| `0x2f` | `se_bonus.wav` | 100 |
| `0x30` | `se_bonus2.wav` | 100 |
| `0x31` | `se_nep00.wav` | 100 |
| `0x32` | `se_boon00.wav` | 0 |
| `0x33` | `se_don00.wav` | 0 |
| `0x34` | `se_boon01.wav` | 0 |
| `0x35` | `se_boon01.wav` | 0 |
| `0x36` | `se_ch02.wav` | 100 |
| `0x37` | `se_ch03.wav` | 0 |
| `0x38` | `se_extend2.wav` | 100 |
| `0x39` | `se_pin00.wav` | 100 |
| `0x3a` | `se_pin01.wav` | 100 |
| `0x3b` | `se_lgods1.wav` | 100 |
| `0x3c` | `se_lgods2.wav` | 100 |
| `0x3d` | `se_lgods3.wav` | 100 |
| `0x3e` | `se_lgods4.wav` | 100 |
| `0x3f` | `se_lgodsget.wav` | 100 |
| `0x40` | `se_msl.wav` | 5 |
| `0x41` | `se_msl2.wav` | 5 |
| `0x42` | `se_pldead01.wav` | 100 |
| `0x43` | `se_heal.wav` | 100 |
| `0x44` | `se_msl3.wav` | 5 |
| `0x45` | `se_fault.wav` | 100 |
| `0x46` | `se_noise.wav` | 100 |
| `0x47` | `se_etbreak.wav` | 0 |
| `0x48` | `se_tan03.wav` | 0 |
| `0x49` | `se_wolf.wav` | 0 |
| `0x4a` | `se_bonus4.wav` | 100 |
| `0x4b` | `se_big.wav` | 100 |
| `0x4c` | `se_item01.wav` | 20 |
| `0x4d` | `se_release.wav` | 100 |
| `0x4e` | `se_changeitem.wav` | 100 |
| `0x4f` | `se_trophy.wav` | 100 |
| `0x50` | `se_warpr.wav` | 100 |
| `0x51` | `se_warpl.wav` | 100 |

## 2. 怎么再来一遍

`tooling/ghidra/scripts/sound_table.py th18`（指针表：字符串数据引用按地址排序）+ `dump_func_asm.py th18 0x476c70` +
`find_imm_refs.py th18 0x4c9b80 0x4c9b84 0x4b47a0`（找到初始化函数），配置表本体直接从 exe 文件偏移 `0xc8580`（`.data` VA `0x4c9b80`）读。
