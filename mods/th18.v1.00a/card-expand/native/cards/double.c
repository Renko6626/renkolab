/* 加倍（id 69）—— 桥牌的 Double（X）：罚分加倍，奖励也加倍。
 *
 *   · Miss 掉 **2** 条命（而不是 1）
 *   · 敌人掉落的道具全部 **×2**
 *
 * 【掉 2 命】挂 +0x0c on_death_after_deathbomb，**不是** +0x14。
 * 死亡序列（engine/card/th18/03-hooks.md §4）：
 *     决死窗口耗尽 → acc = 0; for card: acc |= vtable[0x0c]      ← 我们在这
 *        acc == 0 → Player__commit_death_and_enter_state2 0x45D090（扣命、判 game over）
 *     状态 2 第 3 帧 → 扣火力/撒道具 → 扣钱 → vtable[0x14]        ← 补偿类卡在这
 * 在引擎扣命**之前**多扣 1，它自己的判定就会看到正确的残机数。
 * `0x45d1a0 sub eax,1` 之后两处都是 **js**（判 < 0，不是精确 == -1），所以 1 → 0 → -1 会
 * 正常触发 game over。挂 +0x14 则会绕过那个判定，残机可能停在 -1 而游戏继续。
 * 与 CardTewi 同样的手法：在 +0x0c 里只记账、`return 0` 不救命。
 *
 * ★ 只在 CURRENT_LIVES > 0 时多扣，残机永远不会被我们压到负数（引擎自己那一下照常）。
 *
 * 【掉落 ×2】走 SDK 事件 on_enemy_drop_pre（断点 ce_enemy_drop @ 0x430510 入口，AUDIT §S）：
 * 在引擎**撒之前**把敌人 +0x04 起的 20 个掉落数翻倍，撒的活还是引擎自己干 ——
 * 各 type 的角度、速度、位置都不用我们操心。
 * （+0x30 那个槽是「撒完之后」才广播、且广播完就 memset 清零，在那里改已经晚了。）
 */
#include "sdk.h"

static int on_death_after_deathbomb(ce_card_t *c, uint32_t acc)
{
    (void)c; (void)acc;
    if (CE_CURRENT_LIVES() > 0) {
        CE_CURRENT_LIVES() -= 1;                    /* 引擎紧接着还会再扣 1 → 一次 Miss 共 2 条 */
        ce_log("double: miss costs 2 lives (now %d before the engine's own -1)", CE_CURRENT_LIVES());
    } else {
        ce_log("double: miss with %d lives left, engine's -1 ends the run anyway", CE_CURRENT_LIVES());
    }
    return 0;                                        /* 不救命，只记账 */
}

static void on_enemy_drop_pre(ce_card_t *c, int32_t *counts)
{
    (void)c;
    for (int i = 0; i < CE_ENEMY_DROP_TYPES; ++i)
        if (counts[i] > 0) counts[i] *= 2;
}

CE_CARD(69, .on_death_after_deathbomb = on_death_after_deathbomb,
            .on_enemy_drop_pre = on_enemy_drop_pre);
