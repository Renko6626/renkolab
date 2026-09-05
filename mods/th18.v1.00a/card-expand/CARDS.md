# CARDS —— 已实装的新卡一览

> **版本**：TH18 v1.00a（`th18.exe`，imagebase `0x400000`）。本文裸地址默认属该版本；引用其他版本须写成 `th16:0x…`。
> 人看的目录。**数据的真相在 `patch/th18/cards.js`，行为的真相在 `native/cards/*.c`**；本表每加一张卡补一行。
> id 58–254 可用（≤ 71 张，[`DATA.md`](DATA.md) §4）。状态：✅ 实跑通过 / 🔧 待实跑 / 💡 设计中。

## 黑桃（原型：德州扑克・皇家同花顺）

| id | 名字 | 效果 | 实现（槽 / 事件） | 文件 | 状态 |
| --- | --- | --- | --- | --- | --- |
| 58 | 黑桃 10 | 从道具获得的金钱 +10％（每第 10 个金钱道具多给 1；确定性计数，replay 安全）| `on_item_money` | `s10.c` | 🔧 |
| 59 | 黑桃 J | 移动速度 +10％ | `on_tick_2` 写移速倍率 `player+0x477ec` | `sj.c` | 🔧 |
| 60 | 黑桃 Q | 道具自动回收范围略微增加（吸引半径 70 → 95、吸速 5 → 7；Nitori 是 110）| `on_load` 写玩家回收四参（抄 Nitori）| `sq.c` | 🔧 |
| 61 | 黑桃 K | 自机弹伤害 +10％ | `on_bullet_created` 改 `bullet+0x9c`（抄 Momoyo）| `sk.c` | 🔧 |
| 62 | 黑桃 A | Miss 后的无敌时间 +50％（280 → 420 帧）| `on_tick_2` 识别复活计时器 {279,280} | `sa.c` | 🔧 |

**卡图**：五张用标准英式牌面（Wikimedia Commons，Dmitry Fomin，CC0；`assets/cards/_src/english_pattern/`，`fit_card.py` 出图），sprite 118/119 … 126/127。

🔧 **皇家同花顺**（`cards/royal.c`，五张共用 `.ctor`）：买到第五张黑桃时触发一次——金钱 +800、残机 +2（上限先 +1 钳 7，照 CardLife）、bomb +2（同法照 CardBomb）。判定：ctor 时其余四张已在 `owned[]` 且自己尚未 owned（新获得；每关开始的重调不算）。奖励金钱 888。演出（`ability.anm` script70 父脚本）：五张黑桃卡图每 10 帧一张在场地中央排开 → 60 帧 trophy 音效（0x4f）+ 金色「ROYAL FLUSH」横幅弹出（拉格泰姆钢琴 `ROYAL_RAGTIME` 从第 0 帧起铺整段，帧 60 正好是它第二小节的强拍） → 74 帧「+888 GOLD」→ 170 帧起一起淡出上浮、194 帧消失。AUDIT O26。

## 方片

| id | 名字 | 效果 | 实现（槽 / 事件） | 文件 | 状态 |
| --- | --- | --- | --- | --- | --- |
| 65 | 方片 2 | 商店一次性购买：买下后金钱翻倍（先扣购买价再翻倍；钱不够用火力补差价时结果为 0）；本身不进卡组 | `ctor` 里 `MONEY = 2·M − price`（ctor 先于扣款），`MONEY_TOTAL += 增量`，返回 1 当场销毁 | `d2.c` | 🔧 |

## 致敬・游戏王

| id | 名字 | 效果 | 实现（槽 / 事件） | 文件 | 状态 |
| --- | --- | --- | --- | --- | --- |
| 63 | 强欲之壶 | 购买时立刻获得两张随机卡牌（商店随机池的规则：未拥有、本关可用、按权重）；本身不进卡组 | `ctor` 里 `pick_weighted_random_offer` ×2 → `allocate_new_card(mode 2)`，返回 1 当场销毁（即时卡）。卡图 `POT_OF_GREED`（sprite 132/133，用户原创）| `pot.c` | 🔧 |
| 66 | 神之宣告 | 主动（C 键）：消耗一半残机（向上取整），让 boss 当前符卡立刻按超时结束（无奖励、失败演出）。不在符卡中 / 已超时 / 无残机时拒绝发动（无效音、充能不消耗）。充能 60 s。卡图与演出见下 | `on_activate`：写 boss 中断槽计时到阈值 + 清符卡奖励位；`ce_gui_update_lives` 刷 HUD；拒绝 = `CE_ACTIVATE_REFUSED` | `judgment.c` | 🔧 |
| 67 | 青眼白龙 | 主动（C 键）：献祭 1 残机召唤跟随自机的龙；1500 点生命替玩家挡子弹（每发 −1，弹变点道具）；每 5 秒向上一道光束；生命归零死亡，过关消失。残机 0 拒绝。充能 10 s | `on_activate` 扣命 + 起龙 ANM；`on_active_tick` 跟随（Tenshi lerp）+ `ce_cancel_radius(max = hp)` + `ce_damage_rect`；`on_stage_start`/`on_run_reset` 删 VM | `blue_eyes.c` + `blue_eyes_core.c` | 🔧 |

**青眼白龙（67）补充**：光束 = 45 帧 × 每帧请求 100 的矩形伤害源（2026-09-04 平衡：HP 2500 → 1500、光束 30 → 45 帧）（宽 32、从龙口到区域顶边），**不改** `player+0x47984`，实际每波 ≤ 4500 由引擎每帧上限决定；光束不消弹、激光不挡。跟随目标自机上方 80 px（要石同款 lerp 0.04）、挡弹半径 48、有命中那帧龙染蓝 `0xff0080ff`（要石同款；D3DCOLOR ARGB）；龙下方 66 px 有血条（两个根 VM `drawRect(1,1)`，C 每帧写 `vm+0x54` scale = (56 × hp/1500, 4)，>50％ 蓝 / >20％ 黄 / 红；零售 HUD 充能条同款做法）。卡图（用户原创立绘，`fit_card.py`，sprite 136/137）；场上的龙 = 用户原创俯视图抠黑底（`assets/ability/make_blue_eyes_art.py`，ability sprite 118，script78 缩放 0.45）；光束照魔理沙 Master Spark（零售 `pl01b`/`pl01b2` 贴图 119/120，script79–85：白核 + 四层彩 + 彩光），判定宽 96。设计 `docs/superpowers/specs/2026-09-04-blue-eyes-design.md`，AUDIT O29。

**神之宣告（66）补充**：卡图 `JUDGMENT`（sprite 134/135，用户原创）。发动同时全屏消弹（弹幕 → 点道具 + 激光，引擎 `cancel_all`，O28h）。演出：发动音 0x4d（反转牌同款）+ `ability.anm` script77——卡图副本铺满弹幕区半透明浮现（alpha 140，scale 1.25 → 1.45）、75 帧缓缓放大并上浮 24 px、45 帧后 30 帧淡出。限制：耐久符卡的超时脚本自带掉落照旧（AUDIT O28b）。

## 致敬・UNO

| id | 名字 | 效果 | 实现（槽 / 事件） | 文件 | 状态 |
| --- | --- | --- | --- | --- | --- |
| 64 | 反转牌 | 主动（C 键）：场上所有子弹速度方向反向；充能 60 s。卡图 UNO 反转牌（`fit_card.py`，sprite 128/129）| 第一张主动卡：`active_recharge = 3600`，`on_activate` 扫子弹池翻 `velocity` 与 `angle`（不动激光），并 `ce_anm_spawn` 起 `ability.anm` script68 亮牌（卡图副本绕 Y 轴一圈）| `reverse.c` | 🔧 |

## 其它

| id | 名字 | 效果 | 实现（槽 / 事件） | 文件 | 状态 |
| --- | --- | --- | --- | --- | --- |
| 72 | 炎魔之王拉格纳罗斯 | 主动（C 键）：消耗 2.00 火力召唤**不跟随自机**的炎魔；800 点生命替玩家挡子弹；每 8 秒滑到随机落点，到位后向场上**随机一个**敌人投火球（飞行物，落地爆炸 400）；生命归零死亡，过关消失。火力 < 3.00 拒绝。充能 10 s | `on_activate` 照 Tsukasa 三步（门槛 → `spend_power` → `repopulate`）；`on_active_tick` 挡弹 + 状态机 `fl_step` + 火球位姿 + 落地 8 帧 `ce_damage_rect`；随机走 `ce_rand()`（详见下）。AUDIT §V | `firelord.c` + `firelord_core.c` | 🔧 |
| 70 | 腐化 | 被动：拿到时炸弹上限补满 7；此后**放炸弹消耗的是上限而不是当前数**，且过关不回复 —— 一次给满七发，用一发少一发 | `ctor`（`ce_fresh_acquire` 门控）顶满上限；新 SDK 事件 `on_bomb_spent`（断点 `ce_bomb_spent` @ `0x4203bc`，consume_bomb 刚返回）还原当前数、扣上限；`on_stage_start` 抵消引擎的 `min(3, 上限)` 补给。AUDIT §T | `corruption.c` | 🔧 |
| 69 | 加倍 | 被动：Miss 损失 **2** 条残机；敌人掉落的道具全部 **×2** | 掉命挂 `on_death_after_deathbomb`（引擎扣命**之前**多扣 1，`return 0` 不救命）；掉落走新 SDK 事件 `on_enemy_drop_pre`（断点 `ce_enemy_drop` @ `0x430510` 入口，撒之前把敌人 `+0x04` 起的 20 个掉落数翻倍）。AUDIT §S | `double.c` | 🔧 |
| 68 | 黄昏 | 被动：用掉**最后一颗**炸弹时，那一发结束后自动再放一发 | `on_tick_2` 盯炸弹管理器 `[0x4cf2b8]+0x30` 的两个边沿：0→1 时若 `CURRENT_BOMBS == 0` 就武装，1→0 时调引擎自己的 `do_bomb()` `0x420360`。不开断点、不碰炸弹计数（`0x4574d0` 自带钳 0）。AUDIT §R | `dusk.c` | 🔧 |

**炎魔之王（72）补充**：扣火力照零售 `CardTsukasa__c_press` `0x410e60`——门槛「成本 + 一档」（引擎 `spend_power` 永远保留 1.00，
不留一档实际扣的会比名义少）、`spend_power(200)`、无条件 `repopulate_options`（重建子机 + 广播 `on_power_level_change`）。
火球 = **飞行物 + 落地 8 个定点伤害源**：直线飞向开火时记下的敌人坐标（8 px/帧，非追踪），到点起爆炸特效、放 `0x2c`，之后
连续 8 帧每帧一个 64×64、50 伤害的 `ce_damage_rect`——一个源对同一敌人只结算一次、50 不超四个自机的每帧上限，所以恰好 400。
随机（落点 / 目标）走游戏自己的 `Rng__rand_dword(&REPLAY_SAFE_RNG)` `0x402740` / `0x4cf288`。血条复用青眼的 script86 / 87。
美术：卡图用户立绘（`fit_card.py --fill`，sprite 146/147）；本体用户正面像抠白底 256×256（`ability/make_firelord_art.py`，script91 缩放 0.5）；
火球 / 拖尾 / 爆炸贴图程序生成（同脚本，script92–94）。语音 `FIRELORD_SUMMON`（id `0x55`）/ `FIRELORD_ATTACK`（`0x56`）：用户 ogg 经 `voice/convert_voice.py` 转 wav。
设计 `docs/superpowers/specs/2026-09-06-firelord-design.md`。

## 装备（子机）

| id | 名字 | 效果 | 实现（槽 / 事件） | 文件 | 状态 |
| --- | --- | --- | --- | --- | --- |
| 71 | 破损核心 | 装备：身边多一颗电球子机，每 2 秒朝**最近的敌人**（512 px 内）**瞬间**劈一道电弧，那一个敌人吃 80 伤害 | 第一张走**零售装备卡机制**的卡：`on_power_level_change` 生成子机、`on_tick_2` 计时 + 选目标 + 定点伤害源 + 电弧特效（详见下）。AUDIT §U | `broken_core.c` + `broken_core_core.c` | 🔧 |

**破损核心（71）补充**：子机 = `Player__allocate_option(card, 0x18, ability script88)`（指针存 `ce_state()`，
不是零售的 `card+0x54`：我们的对象只有 `0x54` 字节）。闪电 = **定点伤害源 + 特效**两件独立的事：
`ce_damage_rect(目标坐标, 0, 寿命 2, 80, 24×24)` 钉在敌人身上（Remilia / 青眼同一个原语；一个伤害源对同一敌人
只结算一次，所以正好 80），script89 电弧从电球拉到敌人（C 写 pos / rotation.z / scale.x = 距离 / 256）、
script90 火花在命中点。瞄准角与距离是自己的确定性算术（不引 libm）。
**不改任何游戏资源文件**——第一版曾追加 `pl0X.sht` 的 shooterset 让子机真开火，后来改掉：自机弹天生要飞过去，
与「瞬发单体」相悖。那条链的研究（[`engine/sht/th18/`](../../../engine/sht/th18/README.md)）与工具
（`assets/sht/`）留着给以后真需要「子机连射」的卡。卡图（青色裂核，白底放大居中）与场上电球（黄绿球）是用户原创，电弧（黄白闪电链）程序生成——都过 `assets/ability/make_broken_core_art.py`；卡图 sprite 144/145。

## 约定

- **即时卡**（买了就生效、不进卡组）：`ctor` 或 `dtor` 施加效果后 `return 1`（零售 EXTEND / 六文钱同款，`02-lifecycle.md` §3）。
  这种卡 `deck_visible: 0`（编成里不列，初始携带不调 ctor 会变成死卡）、`repeatable: 1`（可再刷出）。
- 「随机」一律走游戏自己的 RNG 或确定性计数，不引入自己的随机源（replay）。
- 主动卡：`category: 0`，`active_recharge` 给帧数（零售瞬发卡 20–60 s），`on_activate` 返回 0 瞬发 / 1 持续。
- 文案不能含 ASCII `%`，用 `％`。
