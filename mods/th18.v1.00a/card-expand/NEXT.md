# NEXT —— 下一个会话从这里开始：实跑第 7 / 9 / 10 段，然后第二批

> **版本**：TH18 v1.00a（`th18.exe`，imagebase `0x400000`）。本文裸地址默认属该版本；引用其他版本须写成 `th16:0x…`。
> 交接文档。写给**没有本会话上下文**的下一个会话；读完这一页应该能直接动手。

## 0. 现状一句话

一张新卡的 **10 段路全部有了**（[`MAP.md`](MAP.md) §0）：JSON 登记（[`DATA.md`](DATA.md)）+ C 行为（[`SDK.md`](SDK.md)）。
第一批行为卡 = 黑桃 10/J/Q/K/A（id 58–62，`native/cards/`）。**第 7（商店）、9（行为）、10（数据）三段静态审计通过、待实跑。**

| 段 | 状态 |
| --- | --- |
| 1–6 表 / 分配器 / owned / 存档 / 文案 / 图鉴编成 | ✅ 实跑（2026-09-02）|
| 7 商店、10 JSON 数据 | 🔧 待实跑（AUDIT §N）|
| 9 行为（SDK + 黑桃五张 + 强欲之壶 + 反转牌）| 🔧 待实跑（AUDIT §O）← **先做这个** |
| 8 卡图 | 🔧 工具就位（[`assets/`](assets/README.md)）：黑桃五张占位图 sprite 118–127 已进 `_255/th18/abcard.anm`，待实跑 |
| **11 音效表扩容 / 语音** | 🔧 **待实跑**（AUDIT §Q）—— 四张音效表搬进 codecave 加长到 116 行，32 个语音 id `0x54`–`0x73` |

## 0.5 先读什么

[`README.md`](README.md) → [`DATA.md`](DATA.md) → [`SDK.md`](SDK.md) → [`MAP.md`](MAP.md)（追溯表，**每改必补**）→ AUDIT §N、§O。

## 1. 实跑清单（叠 `_255` + `_test`，Windows `git pull` 后）

日志 `th18_card_expand.log` 应有：

```
table: 255 rows filled … NULL/BACK shop weight := 6
grow: … shop loops 255 ids
cards: 58 "黑桃 10" (SPADE_10) tier 5 weight 2 dmode 0 sprites 116/117 initial_unlocked   ← 五行（卡池在 _255 自己的 th18/cards.js）
cards: 5 registered from cards.js; shop pool 397/560 slots, guaranteed offers <= 17/57
cards_dev: start_deck has 5 ids, trace=1
menu: … (56 retail + 5 new + NULL, rest BACK); encyclopedia entries = 61 …
sdk: 58 bound (.on_item_money = on_item_money)         ← 五行
sdk: 5 behaviors, 0 registered cards without behavior; base vtable @ 004b4c78 verified; trace=1
OK: … cards loaded, menu extended, behaviors bound, 100/100 sites verified
```

进游戏：卡组编成里把前五格清空 → 开局：

```
test: initial deck slot 0: empty -> id 58   … slot 4 -> id 62
trace: card 58 object … bound to vtable …    ← 五行
trace: allocate_new_card(id=58, mode=1)  <- NEW ID   … （自动 mark_obtained）
trace: card 59 on_tick_2 (+0x2c) first hit / card 62 on_tick_2 / card 61 on_bullet_created / card 60 on_load / card 58 on_item_money
```

体感：J 移速明显快一点；Q 道具老远就飞过来；K 打 boss 快一点（看血条）；死一次 → A 的无敌时间明显更长（280 → 420 帧）；
10♠：吃满 10 个金钱道具时钱数跳 2（右上角金钱）。商店里五张会以 5–9 档价出现。任何 `FAIL:` / `mitigation:` / 游戏崩溃都是回归——
崩溃优先怀疑：绑定断点的寄存器（O1）、`on_tick_2` 里 `PLAYER_PTR` 为空（已判空）、桩签名（O3）。

**强欲之壶（63）**：商店里买它（300）→ 日志 `pot: gave card X (allocate -> N)` 两行、`trace: card 63 ctor` → 卡组 HUD 多两张、壶本身不在；
它可以再次刷出（`repeatable`）。编成里**不该**出现它（`deck_visible: 0`）。

**反转牌（64，第一张主动卡）**：`cards_dev.js` 起手带 64 → 它出现在主动卡组（HUD 有充能条，一开始满 = 可用）→ 关卡里按 C：
日志 `trace: card 64 c_press`、`reverse: N bullets reversed`，弹幕整体掉头 + Tenshi 的发动音；充能条清空、约 60 s 后回满可再按；
过关充能不丢，局末清零；`_test` 的 `trace` 里 `bound to vtable … (active)`。崩溃优先怀疑：绑定时的 flags / 计时器初值（O19）、`ce_play_sound`（O22）。

通过后：MAP 第 7/9/10 段 🔧 → ✅；AUDIT §N / §O 顶部各记一行「实跑通过」；[`CARDS.md`](CARDS.md) 状态列改 ✅。

## 1b. 商店走两遍（2026-09-04，待实跑）

每关过关后商店开 **2 次**（`shop_core.h` 的 `CE_SHOP_VISITS_DEFAULT`），第二次商品重抽（已买的自动排除）、仍是零售流程（必须买一张）。
实现：`native/shop.c` 两个放行断点（`ce_shop_bought` `0x4183ea` 记成交；`ce_shop_reopen` `0x443b05` 在 GameThread 里把 `0x20000` 位加回 eax），
状态机 `shop_core.c`（主机单测）。引擎链：[`engine/card/th18/05-shop-and-money.md`](../../../engine/card/th18/05-shop-and-money.md) §3.5；审计 AUDIT §P。

日志应有：`shop: 2 visits per stage` → 过关 `shop: opened by msg (visit 1/2 …)` → `shop: bought (…)` → **同一帧** `shop: reopen (visit 2/2 …)`
→ 第二家店（进场动画再来一次，商品不含刚买的）→ `shop: bought` → 正常进下一关。`reopen` 行必须是 `bought + 31`，出现 `(late, gap!)` 就是 P4′ 的空档帧真的发生了。练习模式 / replay 回放里不该出现 `reopen`。
空白卡、买不起、暂停后退到标题都不该多开店（AUDIT P6 / P8）。崩溃优先怀疑：`0x443b05` 处 esi 不是 GameThread（P3）。

通过后：MAP §5 与 AUDIT §P 顶部记「实跑通过」。想改次数就改常量（以后可挂 `cards.js`）；
**关卡中间开店**（MSG opcode 36 或 DLL 直接置 `GameThread+0xb0 |= 0x20000`）技术上可行，但 Stage / Spellcard 不冻结，只该在对话里做——见 §3.5。

## 1c. 神之宣告（id 66，2026-09-04，待实跑）

主动卡：boss 符卡中按 C → 残机减半（向上取整，1 条也能用）→ 符卡立刻按超时结束（血条落到阈值、失败演出、无奖励）。
不在符卡里 / 残机 0 / 没有带超时槽的 boss → 0x10 无效音、充能不消耗。实现 `native/cards/judgment.c`，不开断点；
引擎一手 [`engine/ecl/th18/01-boss-interrupts-and-spellcard.md`](../../../engine/ecl/th18/01-boss-interrupts-and-spellcard.md)，审计 AUDIT O28。
卡图 `JUDGMENT` sprite 134/135（强欲之壶同批 132/133，abcard.anm 已重建）。发动演出 script77（`JUDGMENT_FX` entry15 / sprite117，ability.anm 已重建）：卡图铺满弹幕区半透明浮现 → 放大上浮 → 淡出，共 75 帧，日志带 `flash anm id`；发动同时全屏消弹（弹 → 点道具、激光一起消，O28h）。`cards_dev.js` 起手卡组已带 66。

日志应有：`sdk: 66 bound (.active_recharge = 3600, .on_activate = on_activate)`；符卡里按 C → `judgment: lives 3 -> 1 (cost 2), 1 boss attack(s) expired, spell flags …`
→ 同帧符卡计时 00.00、boss 血条落到阈值、「失败」演出、进下一段；非符 / 无命 / 刚超时那几帧按 C → `judgment: refused (…)` 且充能条仍满。
崩溃优先怀疑：`0x441f10` 的参数顺序（O28c）、`CE_ENEMY_DATA` 0x122c 的推导（O28a 三处交叉）。

## 1d. 青眼白龙（id 67，2026-09-04，待实跑）

主动卡：关卡里按 C → 残机 −1 → 自机上方出现龙（用户原创俯视图，头朝上），跟着自机；弹碰到龙变点道具、龙闪一下蓝色、龙下方血条缩短（蓝 → 黄 → 红）；
第 300 帧起每 5 s 龙头向上一道 Master Spark 式白蓝光束 45 帧（魔理沙贴图，宽约 126、判定 96），boss 血条掉一截（devstage ÷100 一波就死）。1500 发后龙放大淡出。
残机 0 按 C → 无效音、充能不动。过关龙消失。设计 `docs/superpowers/specs/2026-09-04-blue-eyes-design.md`，审计 AUDIT O29，
引擎一手 `engine/player/th18/02-damage-sources.md`。`cards_dev.js` 起手卡组已带 67。

日志应有：`sdk: 67 bound (.active_recharge = 600, …)` → `blue_eyes: summoned, lives 3 -> 2, hp 1500, anm id …` →
`blue_eyes: hp N (blocked …)`（有挡弹的整秒）→ `blue_eyes: wave 1 start at frame 300 (hp …, cap C)`（**记下 cap**，它就是 sht 的 max_dmg，
决定一波实际伤害 ≈ 45 × min(100, cap)）→ `blue_eyes: died after …` 或过关 `blue_eyes: dismissed (stage start) …`；
残机 0 → `blue_eyes: refused (no lives)`。崩溃优先怀疑：O29a/b 的栈参顺序与 XMM、O29c 的 thiscall、`interruptLabel(1)` 是否被 `stop()` 后的 VM 接住
（不接就改成 `ce_anm_delete`）。视觉怀疑：光束是否朝上（子脚本各自 `rotate −90°`，若子 VM 还叠加父旋转也仍是 0 + −90°）、是否从龙头起（父 VM 钉在龙头，子 anchor 左端）；blendMode 9 白核是照魔理沙抄的——坐标假设见 spec §2.3。

## 1e. 音效表扩容 / 语音（2026-09-05，待实跑）

零售音效表是写死的 84 槽（`0x00`–`0x53`），**一个空闲 id 都没有**。四张表（cfg `0x4c9b80`、
wav 名 `0x4b47a0`、slot `0x56c804`、blob `0x56cfe4`）整体搬进 codecave 加长到 116 行 / 104 个 wav 槽，
腾出 **32 个自定义音效 id `0x54`–`0x73`**，第一批装角色语音。51 处 binhack 全是「只换常量」，
唯一手写机器码是 `th18_snd_patch_init` 那 56 字节。引擎一手
[`engine/_shared/th18-sound-table.md`](../../../engine/_shared/th18-sound-table.md)，
设计 `docs/superpowers/specs/2026-09-05-voice-expand-design.md`，审计 [`AUDIT.md`](AUDIT.md) §Q。

语音就是 SE：**可叠加、不做独占通道、不打断**，跟随游戏的 SE 音量。
加一句语音三步：`assets/voice/<NAME>.wav` + `ORDER.txt` 一行 → `patch/th18/voice.js` 一条（带 `id`）
→ `make voice` → 代码里 `ce_play_voice(NAME, x)`。细则 [`assets/voice/README.md`](assets/voice/README.md)。

日志应有：

```
snd: caves cfg=<addr> names=<addr> slots=<addr> blobs=<addr>
snd: voice id 0x54 "TEST_VOICE" -> voice/TEST_VOICE.wav (352924 bytes, wav slot 72, vol 100 pan 0)
snd: OK 1 voices, 116 rows, I1/I2 hold
```

进关卡按 C（反转牌 64）：**Tenshi 发动音与语音同帧一起响** —— 两条一起听见就证明「可叠加」成立。
Alt-Tab 切出切回再按 C，语音仍在。退出游戏不崩。

崩溃 / 异常优先怀疑（对应 AUDIT §Q）：
**没有任何 `snd:` 行** → 断点没触发，查 `0x476410` 的 `expected` 与 cavesize；
**卡在黑屏** → I2 被违反且自检没拦住，`0x4776f0` 在 `Sleep(10)` 死循环（Q3）；
**玩家激光没声音** → 槽 20 指错（Q5）；`snd: FAIL R8` → `0x401139` 的字节界没改对；
`snd: FAIL I1` → `patch_init` 的骨架循环没跑或跑错（Q2）。

`TEST_VOICE` 是**合成的钢琴旋律**（`assets/voice/make_test_melody.py`，2.9 s，纯 stdlib 可复现）：
上行动机 C5–E5–G5–C6 再**逆行**弹回来，落在 C 大三和弦——照反转牌的主题写的。
它是我们自己的内容，所以**入库**，`git pull` 就有；`make voice` 会把它拷进 patch。
真语音就位后换掉它即可（`ORDER.txt` 与 `voice.js` 各改一行）。

通过后：MAP 第 11 段 🔧 → ✅；AUDIT §Q 顶部记一行「实跑通过」。

## 2. 第二批（按优先级）

| 块 | 内容 | 接缝 / 依据 |
| --- | --- | --- |
| ~~皇家同花顺~~ | 🔧 已做（`cards/royal.c`，五张共用 ctor，不开断点；金钱 +800 / 命 +2 / bomb +2），待实跑 | AUDIT O26；`ce_owned()` / `ce_add_life()` / `ce_add_bomb()` 进了 sdk.h |
| **主动卡基类** | C 键 / 充能 / HUD 图标 / replay 复原 | `04-active-cards.md` §3–§6：`c_press` 模板、`+0x38/+0x3c/+0x40` 三件套、flags bit3；SDK 里做一份可继承的「主动卡」桩集 |
| 辅助函数提炼 | 动作出现第二次就进 `sdk.h` | 方案 3 的约定 |
| 图鉴上限 | 新卡 > 71 时才需要：两处 `cmp r,imm8` → cave | AUDIT §M3 |
| ANM 特效 | 🔧 已有第一例：`ce_anm_spawn` + `assets/ability/`（反转牌 script68 亮牌），待实跑；透视真假当场看 | AUDIT O24；`engine/anm/th18/01-vm-instantiate.md` |
| 更多事件 | 按需：击破、符卡开始 / 结束、擦弹… | 每个 = 一个断点 + AUDIT 一条 |

## 2b. 开发辅助（`_test`）

`make ecl`：st01–st06 空壳 + boss 血量 ÷100 + 死时掉 300 金（`assets/ecl/make_dev_ecl.py`）→ **独立 patch `th18_card_expand_devstage`**（`patch-devstage/`，启动器里单独勾，不依赖别的 patch；想打正常弹幕就不勾）；`cards_dev.js` 的 `retail_weight: 6` / `new_weight: 20` 让商店基本只出新卡（在 `_test`）。正式包不受影响。

## 3. 工具链与验收（照旧）

```bash
cd native
make check          # 站点扫描 + 不变式
make step3          # 255 行全套 + 主机单测（cards_def、sdk_core）+ DLL + x87 检查 + files.js
make dllverify
make conflicts OTHERS="<modkit>/thcrap/repos/nmlgc/base_tsa/th18.v1.00a.js …"
make release PUSH=1
```

## 4. 别忘了

- 先读 [`../../LESSONS.md`](../../LESSONS.md)——ABI / 对象模型 / 时序 / 自检 / 崩溃日志的经验都在那。

- 自检门是断点 `ce_gate`，**不要用 `*_mod_post_init`**（AUDIT §H′）。
- **「编译器把什么放在哪一格」的假设都要从上下文重取**（AUDIT §K′、§M6、§O1）。
- 移速类效果只能写 `on_tick_2`（AbilityManager tick 先于 Player tick）；`on_tick` 在复位之前（O7）。
- `+0x14` 死亡槽在复活置无敌计时器**之前**触发；「复活后」的效果用 `on_tick_2` 识别计时器签名（O8）。
- `internal_name` 带 `'\n'` 前缀（N4）；找卡用注册表。
- 装载器 / SDK 全有或全无：任何 FAIL 都还原分配器上界。
- `make release` 只覆盖生成物 + `_test` 的两个 JSON；modkit 里 `patch.js` / README 是手工文案。
- 每条新写入点过 [`../../_template/AUDIT-checklist.md`](../../_template/AUDIT-checklist.md)，追加到 `AUDIT.md`。
