/* 黑桃 10 —— 道具得点 +10%。事件 on_item_score：身价算完、弹窗与计分之前（sdk.c BP_ce_item_score）。 */
#include "sdk.h"

static void on_item_score(ce_card_t *c, int32_t *value)
{
    (void)c;
    *value += *value / 10;
}

CE_CARD(58, .on_item_score = on_item_score);
