/* 黑桃 K —— 自机弹伤害 ×1.1。
 * 抄 CardMomoyo（id 54）的 on_bullet_init：PlayerBullet__create 在 0x45e396 写好 bullet+0x9c（int 伤害）后、
 * 0x45e7f5 调槽 +0x28，0x45e837 再取用。这里就地放大。 */
#include "sdk.h"
#include "royal.h"   /* 皇家同花顺：五张黑桃共用 ctor */

static int on_bullet_created(ce_card_t *c, void *bullet)
{
    (void)c;
    int32_t *dmg = (int32_t *)((uint8_t *)bullet + CE_BULLET_DAMAGE);
    *dmg = *dmg * 11 / 10;
    return 0;
}

static int royal_tick(ce_card_t *c) { ce_royal_tick(c); return 0; }
CE_CARD(61, .ctor = ce_royal_flush_ctor, .on_tick_2 = royal_tick, .on_bullet_created = on_bullet_created);
