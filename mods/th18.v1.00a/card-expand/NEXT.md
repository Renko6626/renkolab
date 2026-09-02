# NEXT —— 下一个会话从这里开始：战线 D（存档）

> **版本**：TH18 v1.00a（`th18.exe`，imagebase `0x400000`）。本文裸地址默认属该版本；引用其他版本须写成 `th16:0x…`。
> 交接文档。写给**没有本会话上下文**的下一个会话；读完这一页应该能直接动手。

## 0. 现状一句话

卡表已搬进 codecave（255 行）、分配器已搬（id 0–254 可分配）、`zAbilityManager.owned[]` 已扩到 255；
`allocate_new_card(id=58)` 在用户机器上**实跑成功**。**卡住新卡的只剩存档**：卡组编成选新卡时提示
「未获取」，因为 `unlocked_cards[id]` 读的是 `zScoreFile` 里那个 `uint8_t[57]` 之后的字节。

| 战线 | 状态 |
| --- | --- |
| A 搬表 | ✅ 实跑（步骤 1、2）|
| B 分配器 | ✅ 实跑（步骤 3）|
| C `zAbilityManager` 扩容 | 🔧 静态审计通过，**已发布未实跑**（用户 `git pull` 后重跑步骤 2/3 即验）|
| **D 存档** | ← **这里** |
| E 图鉴 / 顺序表 / 文案 / 图 / 商店筛选 | 未开始 |

## 1. 先读什么（按顺序，20 分钟）

1. [`README.md`](README.md) —— 这个 mod 是什么、三个工具各干什么、怎么发布。
2. [`../card-rework/PLAN-255-ids.md`](../card-rework/PLAN-255-ids.md) §2 **战线 D** —— 11 处访问点的逐条改写表（已算好长度）。
3. [`AUDIT.md`](AUDIT.md) §H′ —— **为什么自检门是断点不是 `post_init`**（thcrap 的 merge bug），别再踩。
4. [`../../../engine/card/th18/11-sentinels-56-57.md`](../../../engine/card/th18/11-sentinels-56-57.md) §1 —— `+0x24` 初期解禁字段与 `ScoreFile__init_unlocked_cards_from_table`。

## 2. D 要做什么

**目标**：新卡（id ≥ 58）的解锁状态可读、可写、可持久化；**`scoreth18.dat` 逐字节不变**。

**已定的设计**（PLAN §2 战线 D）：`unlocked_cards` 整个搬进一块 255 字节的 codecave（影子数组），
11 处访问全部改成 `disp32(%idx)` 形态（去掉存档基址寄存器），每处变短或等长、`nop` 补齐。

**本会话补充的一条设计决定（建议采纳）**：影子数组对 **id < 57 要回写零售存档**，否则打补丁期间
解锁的零售卡在卸载后会丢。即：

- 读：全部走影子；
- 写（`CardCollection__mark_obtained_and_notify` `0x418e04`、`ScoreFile__unlock_all` `0x4648fc`）：写影子，**id < 57 时同时写 `scorefile+0x5f588+id`**；
- 门里初始化：影子 `[0..56]` ← 零售存档（真相），影子 `[57..254]` ← side-car 文件；
- 持久化：`mark_obtained` 时 write-through 到 side-car（255 字节小文件，不用等存档写盘）。

这样零售 id 的真相仍在 `scoreth18.dat`，新 id 的真相在 side-car，**两边都不会因为另一边而丢**。

## 3. 站点（全部一手，长度已核）

| 地址 | 原指令 | 长 | 改成 | 备注 |
| --- | --- | --- | --- | --- |
| `0x41440b` | `cmp %cl, 0x5f588(%eax,%edx)` | 7 | `cmp %cl, SHADOW(%edx)` 6 + nop | 图鉴 |
| `0x4149ec` | `cmpb $0, 0x5f588(%esi,%eax)` | 8 | `cmpb $0, SHADOW(%eax)` 7 + nop | 卡组编成 |
| `0x416590` | `cmpb $0, 0x5f588(%eax,%ebx)` | 8 | 同上形态 | `FUN_00416540`——**「未获取」就是这里** |
| `0x41694e` | `cmpb $0, 0x5f588(%eax,%edx)` | 8 | 同上 | `FUN_00416940` |
| `0x416e3d` | `cmp %al, 0x5f588(%edx,%ecx)` | 7 | 6 + nop | `CardData__is_available_at_stage` |
| `0x417125` | `cmpb $0, 0x5f588(%eax,%esi)` | 8 | 7 + nop | 商店随机池 |
| `0x417ea3` | `cmpb $0, 0x5f588(%ecx,%eax)` | 8 | 7 + nop | `AbilityShop__on_tick` |
| `0x418df6` | `cmpb $0, 0x5f588(%esi,%edi)` | 8 | 7 + nop | `mark_obtained` 读 |
| `0x418e04` | `movb $1, 0x5f588(%esi,%edi)` | 8 | **`call cave` 5 + 3 nop**（双写） | `mark_obtained` 写 ★ |
| `0x418e15` | `movb 0x5f588(%esi,%eax), %al` | 7 | 6 + nop | 全收集遍历 |
| `0x4648fe` | `lea 0x5f588(%ebx), %eax`（前面 `push $0x38`） | 6 | 建议不动 | `unlock_all` 只清零售 56 项；新 id 的 unlock_all 由 DLL 自己做 |
| `0x4636d7` | `movb %al, 0xd0(%edi,%edx)` | 7 | 视设计 | `init_unlocked_cards_from_table` 写的是**存档副本**，门里初始化影子时可以不管它 |

`SHADOW(%reg)` 用 thcrap 的 `<codecave:th18_card_unlocked>` 绝对地址：`cmpb $0, disp32(%eax)` = `80 b8 <disp32> 00`。
每个寄存器的 ModRM 各不相同——**用生成器算，别手写**（`sites.py` 里加一类 `emit_unlock_binhacks`）。

## 4. 还要逆向的（D 的唯一未知项，但采用 write-through 设计后可以**不做**）

`scoreth18.dat` 什么时候写盘、由谁写。线索：`ScoreFile__load` `0x4637d0` 里 `FUN_004639b0` 像是校验/加密；
字符串 `"scoreth18.dat"` 的 xref；`FUN_004914c0` 是 `memcmp`-类比较。
**如果 side-car 用 write-through（每次 `mark_obtained` 就写文件），这一项可以跳过。**

## 5. 工具链与验收（照旧）

```bash
cd native
make check          # 站点扫描 + 不变式
make step3          # 255 行全套（含 C）+ patch-test
make dllverify dllx87
make release PUSH=1 # 同步进发布仓库 th18_modkit，Windows 只 git pull
```

D 的验收：叠 `patch-test`、把空槽改发 id 58 → 卡组编成里**能选**它、开局能拿到；退出再进，**仍然是解锁的**
（side-car 生效）；`scoreth18.dat` 的 md5 与打补丁前**相同**（除非解锁了零售卡）。
日志加一行 `unlocked: shadow @ …, 57 retail + N side-car`。

## 6. 别忘了

- 自检门是断点 `ce_gate`，新增的运行时逻辑放进 `BP_ce_gate` 里的 `ce_selfcheck` 或再挂一个断点；**不要用 `*_mod_post_init`**（AUDIT §H′）。
- `sites_gen.h` 与行数无关，DLL 一份配所有 patch；D 的站点也按这个原则做（改后字节 = cave + 常量偏移）。
- 日志路径必须从 `GetModuleFileNameA(NULL)` 拼绝对路径（AUDIT H14）。
- `make release` 只覆盖生成物；modkit 里的 `patch.js` / 侧车 `.json` / README 是手工文案，改了要在那边单独提交。
- 每条新写入点过 [`../../_template/AUDIT-checklist.md`](../../_template/AUDIT-checklist.md)，追加到 `AUDIT.md` 新一节。
- `0x418e04` 那个双写 cave 是 D 里**唯一一段手写机器码**——反汇编回来比对（AUDIT §A 的做法）。
