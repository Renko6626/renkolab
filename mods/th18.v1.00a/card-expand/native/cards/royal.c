/* 皇家同花顺 —— 五张黑桃齐了触发：金钱 +800、命 +2、bomb +2。
 *
 * 触发点不另开断点：卡只能从商店买到，成交时 allocate_new_card(mode 2) 会调该卡的 ctor（02-lifecycle §3），
 * 而 owned[id] = 1 写在 ctor 之后（0x412d42）——所以 ctor 里看「其余四张是否已 owned」，齐了就是第五张，正好只触发一次。
 * 初始携带（mode 1）不调 ctor，编成里带满五张不算（用户设定：只有买齐才算）。
 *
 * 命 / bomb 照零售 CardLife / CardBomb 的 dtor：先把上限 +1（钳 7），再调引擎的加法（钳上限、放音效、起特效）。
 * 返回 0：黑桃是正常卡，要入卡组。 */
#include "royal.h"

static const uint32_t SPADES[5] = { 58, 59, 60, 61, 62 };

int ce_royal_flush_ctor(ce_card_t *c)
{
    uint32_t self = ce_card_id(c);
    if (!ce_royal_flush_ready(CE_OWNED_ARRAY(), self, SPADES, 5)) return 0;
    if (!CE_GAME_THREAD()) { ce_log("royal: complete but not in game thread, skip"); return 0; }
    int32_t m = CE_MONEY();
    CE_MONEY() = m + 800;
    CE_MONEY_TOTAL() += 800;
    for (int i = 0; i < 2; ++i) {
        if (CE_LIVES_MAX() < 7) CE_LIVES_MAX() += 1;     /* CardLife__destructor 0x409b80 的写法 */
        ce_add_life();
    }
    for (int i = 0; i < 2; ++i) {
        if (CE_MAX_BOMBS() < 7) CE_MAX_BOMBS() += 1;     /* CardBomb__destructor 0x409c20 的写法 */
        ce_add_bomb();
    }
    ce_log("royal: ROYAL FLUSH by card %u — money %d -> %d, lives %d (max %d), bombs %d (max %d)",
           self, m, CE_MONEY(), CE_CURRENT_LIVES(), CE_LIVES_MAX(), CE_CURRENT_BOMBS(), CE_MAX_BOMBS());
    return 0;
}
