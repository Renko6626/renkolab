# NEXT —— 下一个会话从这里开始：行为 SDK

> **版本**：TH18 v1.00a（`th18.exe`，imagebase `0x400000`）。本文裸地址默认属该版本；引用其他版本须写成 `th16:0x…`。
> 交接文档。写给**没有本会话上下文**的下一个会话；读完这一页应该能直接动手。

## 0. 现状一句话

一张新卡的 **10 段路里 9 段有了**（[`MAP.md`](MAP.md) §0）：JSON 登记（[`DATA.md`](DATA.md)）→ 图鉴 / 编成 / 商店里出现 →
能买、能拿、能存档、名字说明是自己的。**只差行为**：新 id 的跳转表项指向 case 56（无行为构造器），拿到手什么也不发生。

| 段 | 状态 |
| --- | --- |
| 1–6 表 / 分配器 / owned / 存档 / 文案 / 图鉴编成 | ✅ 实跑（2026-09-02）|
| 7 商店、10 JSON 数据 | 🔧 **静态审计通过，待实跑**（AUDIT §N）← 先做这个 |
| 8 卡图 | 手工：写卡的人改 ANM，JSON 给索引 |
| **9 行为** | ⏳ ← **本轮** |

## 0.5 先读什么

[`README.md`](README.md) → [`DATA.md`](DATA.md)（写卡的人看的）→ [`MAP.md`](MAP.md)（追溯表，**每改必补**）→
[`AUDIT.md`](AUDIT.md) §N（商店 + 装载器）→ 行为相关的引擎知识：
[`engine/card/th18/02-lifecycle.md`](../../../engine/card/th18/02-lifecycle.md)（对象生命周期 / 虚表）、
[`03-hooks.md`](../../../engine/card/th18/03-hooks.md)（卡能挂的钩子）、
[`04-active-cards.md`](../../../engine/card/th18/04-active-cards.md)、AUDIT §A（`0x412cd5` 公共尾段的栈契约）。

## 1. 先实跑第 7 + 10 段

`make release PUSH=1` 已把 DLL + 三个 patch 同步到 modkit；Windows 只 `git pull`。叠 `_255` + `_test`，看日志：

```
table: 255 rows filled at …  (58 retail + 197 NULL copies); NULL/BACK shop weight := 6
grow: zAbilityManager 0xd70 -> 0x116c, owned[] at +0xd70 (255 entries), shop loops 255 ids
cards: 58 "测试卡牌" (TEST58) tier 5 weight 2 dmode 0 sprites 116/117
cards: 1 registered from cards.js; shop pool 369/560 slots, guaranteed offers <= 17/57
menu: order table @ … rebuilt (56 retail + 1 new + NULL, rest BACK); encyclopedia entries = 57; …
OK: table filled (255 rows @ …), allocator relocated, manager grown, unlocked shadowed, text redirected, cards loaded, menu extended, 100/100 sites verified
unlocked: shadow @ …, 57 retail (N set) + side-car (M new ids set) + 0 initial_unlocked from …
```

游戏里：图鉴 / 编成里「测试卡牌」两行说明是 JSON 的；**商店**里它会以中价档出现（权重 2，未拿过 +5 份 → 7/369 的概率，
多开几次店），能买（零售池最坏 362 份 + 它 7 份）；买了以后重启仍解锁；商店里**不该**出现 NULL / BACK。任何 `FAIL:` / `mitigation:` 都是回归。
通过后把 MAP 第 7 / 10 段的 🔧 改 ✅，AUDIT §N 顶部记一行。

## 2. 行为 SDK 要做什么

目标：写一张有行为的新卡 = 一个 `.c` 文件 + JSON 一条；SDK 写一次。

| 块 | 内容 | 依据 / 待反 |
| --- | --- | --- |
| 对象布局 | zAbility 基类大小、字段（`+0x4c` = 表行指针，`allocate_new_card` 存的）、两个 `zTimer` | `02-lifecycle.md`、`01-object-model.md` |
| 虚表模板 | 基类虚表的槽位与签名（`__thiscall`，mingw 用 `__attribute__((thiscall))`）；DLL 里一份可拷贝的虚表，回调指向 C | `02-lifecycle.md`；反 case 56 的构造器看它填哪个虚表 |
| 构造器契约 | 跳转表项指过去时寄存器 / 栈的状态；公共尾段 `0x412cd5` 要求（AUDIT §A） | 反 case 56（`0x411489`）与任一有行为的 case（如 id 5 PENDULUM）|
| 绑定 | `cards.c` 装完 JSON 后，按 id 把 DLL 里登记的构造器写进跳转表 cave（`fill_jumptable` 之后）；JSON 有卡而 DLL 无行为 → 日志「无行为」；DLL 有行为而 JSON 无卡 → FAIL | `selfcheck.c` |
| 引擎访问 | 头文件：`MONEY` `0x4ccd34` 等全局、玩家、`Rng`、道具生成——从 `01-object-model.md` §7 抄 | — |
| 克隆 | `"behavior": "clone:<零售 id>"`：跳转表项指向零售构造器。**先反**零售构造器是否从表行 / 自身 id 取参数，否则克隆卡会以原 id 的身份激活 | 小 RE 题 |
| 示范 | 一张真有行为的卡（比如「获得时 +100 金钱」：`MONEY += 100`、`MONEY_TOTAL_COLLECTED += 100`）| `05-shop-and-money.md` §1 |

## 3. 工具链与验收（照旧）

```bash
cd native
make check          # 站点扫描 + 不变式
make step3          # 255 行全套 + 主机单测（cards_def）+ DLL + x87 检查 + files.js
make dllverify
make conflicts OTHERS="<modkit>/thcrap/repos/nmlgc/base_tsa/th18.v1.00a.js …"
make release PUSH=1 # dist → 同步进 th18_modkit（含 _test 的 th18/cards.js）→ 提交 → 推
```

## 4. 别忘了

- 自检门是断点 `ce_gate`，**不要用 `*_mod_post_init`**（AUDIT §H′）。
- **凡是「编译器把什么放在哪一格」的假设都要从上下文重取**（AUDIT §K′、§M6）。行为 SDK 的虚表槽位 / 栈契约同理。
- `sites_gen.h` 与行数无关，DLL 一份配所有 patch。
- 装载器全有或全无；56/57 行 `+0x14 := 6` 在 `fill_table`，不依赖装载器成功（AUDIT N3）。
- `internal_name` 存的带 `'\n'` 前缀（AUDIT N4）——行为 SDK 若要按名字找卡，别用表行 `+0x00`，用注册表。
- `make release` 只覆盖生成物 + `_test/th18/cards.js`；modkit 里 `patch.js` / README 是手工文案，改了要在那边单独提交。
- 每条新写入点过 [`../../_template/AUDIT-checklist.md`](../../_template/AUDIT-checklist.md)，追加到 `AUDIT.md` 新一节。
