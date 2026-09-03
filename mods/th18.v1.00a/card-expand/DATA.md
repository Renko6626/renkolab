# DATA —— 用 JSON 登记一张新卡

> **版本**：TH18 v1.00a（`th18.exe`，imagebase `0x400000`）。本文裸地址默认属该版本；引用其他版本须写成 `th16:0x…`。
> 面向**写卡的人**：一张卡里所有不需要编译的部分——表行、文案、sprite 索引、商店参数——都从这里进游戏。
> 行为（获得时 / 每帧 / 激活时做什么）不在这里：那是 DLL 里的 C 代码，按 id 绑定，见 [`SDK.md`](SDK.md)。

## 0. 一张卡的三层

| 层 | 在哪 | 谁写 | 什么时候能看到效果 |
| --- | --- | --- | --- |
| **登记**（本文）| 任何 thcrap patch 的 `th18/cards.js` | 你，JSON | 下次启动：图鉴 / 编成 / 商店里出现，能买、能拿、能存档 |
| **卡图** | `abcard.anm` 的 sprite | 你，thanm/truanm | JSON 里填索引即可，DLL 不碰 ANM |
| **行为** | `native/cards/` 里一个 `.c`（[`SDK.md`](SDK.md)）| 你，C | 下次启动 |

先写登记，卡就已经能在游戏里走完一圈（无行为）；再写行为。两层能分开排错。已实装的卡见 [`CARDS.md`](CARDS.md)。

## 1. 文件在哪、怎么合并

DLL 在开机自检门里调 thcrap 的 `stack_game_json_resolve("cards.js")`，thcrap 把栈里**每个** patch 的
`th18/cards.js`（也认 `th18/cards.js.v1.00a`）按 patch 顺序**深合并**成一个对象。所以：

- 任何 patch 都能加卡：放一个 `th18/cards.js` 就行，不必碰 `th18_card_expand_255`。
- 两个 patch 写了同一个 id → 后进栈的字段覆盖先进栈的（thcrap 语义），DLL 只能看到合并后的结果，不会报「被覆盖」。
- 文件缺失 = 0 张新卡，不是错误。`th18_card_expand_255` 自己带本 mod 的卡池（`patch/th18/cards.js`，现在是黑桃五张）；别的 patch 叠加自己的。
- 别忘了把 `th18/cards.js` 写进该 patch 的 `files.js`（`make files` 会递归收）。

## 2. 格式

顶层是对象，**键 = id 的十进制字符串**，范围 **58–254**（56 = NULL 空槽、57 = BACK 卡背，零售哨兵，不能占）。
一个 patch 最多登记多少张见 §4。

```json
{
  "58": {
    "name": "测试卡牌",
    "desc": ["第一行说明", "第二行说明"],
    "internal_name": "TEST58",
    "price_tier": 5,
    "weight": 2,
    "dmode": 0,
    "repeatable": 0,
    "deck_visible": 1,
    "initial_unlocked": 0,
    "hud_show": 1,
    "category": 2,
    "f08": 0,
    "sprite_large": 116,
    "sprite_small": 117
  }
}
```

| 字段 | 写进 `zTableCardData` | 必填 | 默认 | 取值 | 备注 |
| --- | --- | --- | --- | --- | --- |
| `name` | 文案行 0 | ✅ | — | UTF-8，≤ 63 字节 | **不能含 ASCII `%`**：文案会被当 printf 格式串（`0x4873f0` → `0x404e40`）。要写百分号用全角 `％`（U+FF05）|
| `desc` | 文案行 1–6 | — | 空 | 数组，≤ 6 项，每项 UTF-8 ≤ 63 字节 | 同样不能含 `%` |
| `internal_name` | `+0x00` | — | 键本身 | ASCII ≤ 31 字节 | 只作调试。DLL 存的是 `"\n" + 名字`：`ability.txt` 的解析器按这个字段找卡，新 id 的文案不能走那条路（会写到 `zAbilityText` 外面），带换行的名字永远匹配不上（AUDIT §N4）|
| `price_tier` | `+0x10` | ✅ | — | 0–14 | 价格表 `0x4b35c4` 的下标。零售：1–6 低价档（50–180）、7–9 中价档（200–280）、10–14 高价档（300–500）|
| `weight` | `+0x14` | ✅ | — | 0–255 | 商店随机池里压几份。**0 = 必出资源卡**（EXTEND/BOMB 那一类，进「保证」循环）；**6 = 永不进随机池**；从没拿过的卡再 +5 份 |
| `dmode` | `+0x18` | — | 0 | 0–12 | 出现规则，见 [`engine/card/th18/05-shop-and-money.md`](../../../engine/card/th18/05-shop-and-money.md) §5：0 恒可用；1–5 = 只在该关必出；6–10 关卡区间；11/12 看解锁位 |
| `repeatable` | `+0x1c` | — | 0 | 0/1 | 1 = 已拥有也会再进商店 |
| `deck_visible` | `+0x20` | — | 1 | 0/1 | 卡组编成里列出 |
| `initial_unlocked` | `+0x24` | — | 0 | 0/1 | 1 = 不用获得就已解锁（见 §3）|
| `hud_show` | `+0x28` | — | 1 | 0/1 | 在被动卡 HUD 行画出来 |
| `category` | `+0x0c` | — | 2 | 0–4 | 🟡 语义是从零售 dump 推的：0 主动卡、1 角色卡、2 装备、3 资源、4 哨兵（别用 4）|
| `f08` | `+0x08` | — | 0 | 0/1 | 语义未知（`OPEN-questions.md` §2），零售取 0/1，照原名给出 |
| `sprite_large` | `+0x2c` | ✅ | — | 整数 | `abcard.anm` 的 sprite 索引，DLL 不校验范围 |
| `sprite_small` | `+0x30` | ✅ | — | 整数 | 同上 |

- 所有整数字段必须是 JSON 整数（`5`），不是字串（`"5"`）；thcrap 的 `0x` 十六进制字串**不**支持。
- 不认识的字段：日志一行警告，不算错。
- `+0x04` 由 DLL 写成 id，你不用管；行号 = id（`TableCardData__get` 线性查 `+0x04`，所以行号其实无所谓）。

## 3. 解锁与存档

零售的 `initial_unlocked`（`+0x24`）是新档创建时逐 id 拷进 `unlocked_cards` 的，那个循环只走 0–57。
新卡改成：**每次读档时**，`initial_unlocked = 1` 的新卡在解锁影子数组里直接置 1。解锁是单调的、新档也该解禁，
所以和零售语义等价，side-car 格式不变。

新卡的解锁真相在 `%APPDATA%\ShanghaiAlice\th18\th18_card_expand.sav`（[`README.md`](README.md) 战线 D）。
**id 就是存档键**——改了 JSON 的键，解锁记录就跟着错位，这是键用 id 不用名字的代价与理由。

## 4. 硬上限（超了整包 FAIL，不会半张卡进游戏）

| 上限 | 数 | 来源 |
| --- | --- | --- |
| 新卡总数 | **≤ 71** | 图鉴条目数 56+N 写进两处 `cmp r, imm8`（AUDIT §M）|
| 商店随机池总份数 `Σ(weight+5)`（weight ∉ {0,6}，零售 + 新卡）| **≤ 560** | `pick_weighted_random_offer` `0x8c0` 栈缓冲（边界 #34）；零售最坏 362，剩 198 份 ≈ 28 张权重 2 的新卡 |
| 必出卡数 `count(weight==0) + count(dmode∈1..5)` + 6 | **≤ 57** | offer 栈数组 `[ebp-0xe4]`（边界 #34）；零售 5 + 6 + 6 = 17 |

DLL 装载时按合并后的表**现算**这三条，超了写 `FAIL:` 并把分配器上界还原到零售值——整个扩容包等于没装。

## 5. 装载时机与失败策略

`BP_ce_gate`（`ScoreFile__load` 入口）里，顺序是：填表 → 跳转表 → 扩容核对 → 影子数组 → 文案断点 →
**装载 `cards.js`** → 图鉴 / 顺序表（消费注册表）→ 100 处站点回读。

任何一条错（JSON 语法、键不是整数、id 越界 / 重复、字段缺失 / 越界、`%`、超长、超上限、thcrap/jansson 导出拿不到）
→ `FAIL: cards: …` + 还原分配器上界。日志在游戏目录 `th18_card_expand.log`；成功时每张一行
`cards: 58 "测试卡牌" (TEST58) tier 5 weight 2 dmode 0 sprites 116/117`，再一行汇总
`cards: N registered from cards.js; shop pool P/560 slots, guaranteed offers <= G/57`。

## 6. 卡图（你自己做）

新卡行的 `+0x2c/+0x30` 就是 sprite 索引。用 thanm/truanm 往 `abcard.anm` 加 sprite，以文件替换的方式随 patch 分发
（thcrap 的 `th18/abcard.anm`），把索引填进 JSON。已知零售用到 116/117；索引余量 ⏳ 未查，加的时候数一下并回填到
[`engine/card/th18/10-extensibility-limits.md`](../../../engine/card/th18/10-extensibility-limits.md)。

## 7. 示范

本 mod 的卡池在 `patch/th18/cards.js`（黑桃 10/J/Q/K/A，id 58–62，`initial_unlocked: 1` 所以一开局就能在编成里选）。
`_test` 只放开发配置 `cards_dev.js`（起手卡组 / trace）。
