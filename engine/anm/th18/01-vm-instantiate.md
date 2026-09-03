# anm/th18 §1 — 从已装载 ANM 起一个 VM（instantiate / set_sprite / 按 id 删）

> **版本**：TH18 v1.00a（`th18.exe`，imagebase `0x400000`）。本文裸地址默认属该版本；引用其他版本须写成 `th16:0x…`。
> 一手反编译（2026-09-04），为 card-expand 的「发动亮牌」特效而反；ANM 装载器与脚本 VM 本身**没碰**，仍见 [OVERVIEW](../OVERVIEW.md)。

## 0. 结论

| 函数（ExpHP 名） | 地址 | ABI | 做什么 | 可信度 |
| --- | --- | --- | --- | --- |
| `AnmLoaded__instantiate_vm_to_world_list_back` | `0x405bf0` | thiscall(`AnmLoaded*`; `int* out_id`, `int script`, `int layer`, `void** out_vm`) **ret 0x10** | 从该 anm 的脚本表克隆一个 VM、实体坐标置 (0,0,0)、`layer ∈ [0,0x18)` 时写 `vm+0x18` 并置标志、跑一帧、挂 world 列表尾、把 id 写回 `*out_id` | ✅ |
| `AnmLoaded__set_sprite` | `0x477b00` | thiscall(`AnmLoaded*`; `vm`, `sprite_idx`) **ret 8** | 按 sprite 表（`anm+0x11c`，每项 0x44）给 VM 写 UV / 尺寸；`anm+0x108 == 0`（未装载）返回 −1 | ✅ |
| `AnmManager__sub_488cf0` | `0x488cf0` | stdcall(`anm_id`) **ret 4** | `get_vm_with_id` 找到就标记删除（`vm+0x538 |= 0x80`）并递归子树 | ✅ |
| `AnmManager__interrupt_tree` | — | (`anm_id`, `n`) | 让脚本跳到 `interruptLabel(n)`（Tenshi 收尾用 1 = 淡出） | 🟡 只看了调用点 |

## 1. 发现

`CardTenshi__c_press` `0x40ebf0` 发动时**内联**了一份 `0x405bf0` 的逻辑：`ABILITY_MANAGER->ability_anm(+0x10)` → `+0x134` 引用计数 +1 →
`AnmManager__allocate_new_vm` → `AnmManager__sub_407420(anm, vm, 0x1c)`（把脚本表第 0x1c 项、步长 0x60c、共 0x151 dword 拷进 VM）→
`vm+0x18 = 13`（层）→ 标志 `&= ~0x200000 | 0x101000` → `vm+0x5f0..0x5f8` = 卡记下的玩家坐标 → `AnmVm__run` → `insert_in_world_list_back` → id 存 `card+0x1c`。
独立函数版把坐标固定成 (0,0,0)。HUD / 编成 / 图鉴则用 `abcard_anm(+0x0c)` 走 `instantiate_vm_to_ui_list_front` 再 `set_sprite(entry+0x2c)`
（[`../../card/th18/11-sentinels-56-57.md`](../../card/th18/11-sentinels-56-57.md)）。

## 2. 验证

- `0x405bf0` 反汇编：`mov edi, ecx`（this）、`[ebp+8]` out_id、`[ebp+0xc]` script、`[ebp+0x10]` layer、`[ebp+0x14]` out_vm，尾 `ret 0x10`——唯一出口。
- `0x477b00`：两个出口都 `ret 8`（`+0x108 == 0` 早退与正常路径）。
- `0x488cf0`：`push [ebp+8]` 后调 `get_vm_with_id`，唯一出口 `ret 4`。
- `sub_407420` 的脚本表：`anm+0x10c` 基址、步长 `0x60c`——与 [`../th16/README.md`](../th16/README.md) 里 th16 的「`mgr+0x10c` 步长 `0x5fc` 模板数组」同构（th18 模板多 0x10 字节）。

## 3. 坐标与层（与 ANM 脚本的配合）

- 实体坐标 `vm+0x5f0` 是 ECL 坐标；配合脚本里 `originMode(1)`，(0,0) 就是**场地正中**（thpages: origin 1 = ECL (0,0) in stages 1–3）。
- `layer` 参数写 `vm+0x18`；脚本里的 `layer(n)` 会再覆盖。零售「场地中央展示卡」的 `abcard.anm script14` 用 `layer(16)`（子弹之上）；Tenshi 要石用 13。
- 一次性特效让脚本自己 `delete()`，卡对象不必记 id；需要外部收尾才走 `interrupt_tree` + `0x488cf0`（Tenshi 模式）。

## 4. 用法（card-expand）

`mods/th18.v1.00a/card-expand/native/sdk.h` 的 `ce_anm_spawn(anm, script, layer)` 只包 `0x405bf0`；
反转牌发动时起 `ability.anm` 追加的 `script68`（卡图副本 `sprite109`，`type(8)` 绕 Y 轴一圈），AUDIT O24。

## 5. 未答

- 世界层（stage 1–3）的投影是否透视：决定 `type(8)` 绕 Y 转有没有近大远小。🟡 待实跑一眼定；是正交就改用 `posTime` 推 z 或放弃伪 3D。
- `AnmManager__interrupt_tree` 的 ABI 没看（未用）。
