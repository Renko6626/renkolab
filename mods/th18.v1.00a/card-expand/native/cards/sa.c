/* 黑桃 A —— Miss 后无敌时间 +50%。
 * 复活时 Player tick 在 0x45c35e 把无敌计时器置 {prev 0x117, cur 0x118, 280.0}。这个 (280, 279) 的组合只在
 * 刚置好的那一帧出现（之后 prev = 上一帧 cur），炸弹 / 决死救回写的是别的值。AbilityManager tick 先于 Player tick，
 * 所以 on_tick_2 在下一帧 Player 递减之前看到它 → 放大到 420。 */
#include "sdk.h"

static int on_tick_2(ce_card_t *c)
{
    (void)c;
    if (!CE_PLAYER()) return 0;
    ce_timer_t *t = CE_PLAYER_INVULN();
    if (t->cur == CE_RESPAWN_INVULN_FRAMES && t->prev == CE_RESPAWN_INVULN_FRAMES - 1) {
        int32_t n = CE_RESPAWN_INVULN_FRAMES * 3 / 2;
        t->cur = n; t->prev = n - 1; t->cur_f = (float)n;
    }
    return 0;
}

CE_CARD(62, .on_tick_2 = on_tick_2);
