/* shop_core.c —— 「商店走两遍」的状态机（纯逻辑；说明见 shop_core.h）。 */
#include "shop_core.h"

void ce_shop_reset(ce_shop_state_t *s, int visits)
{
    s->visits       = visits < 1 ? 1 : visits;
    s->visits_left  = 0;
    s->bought       = 0;
    s->bought_stage = -1;
    s->bought_frame = -1;
}

void ce_shop_on_bought(ce_shop_state_t *s, int stage, int frame)
{
    s->bought       = 1;
    s->bought_stage = stage;
    s->bought_frame = frame;
}

int ce_shop_on_gamethread(ce_shop_state_t *s, int flag_set, int shop_open, int stage, int frame, int blocked)
{
    if (flag_set) {                                  /* MSG 要求开第一家：本关名额从头算 */
        s->visits_left = s->visits - 1;
        s->bought = 0;
        return 0;
    }
    if (shop_open || !s->bought) return 0;
    /* 店刚关、本次进店成交过：只在「同关、成交后不久」才算数，其余一律作废（回标题 / 新一局） */
    int fresh = stage == s->bought_stage
             && frame >= s->bought_frame
             && frame - s->bought_frame <= CE_SHOP_REOPEN_WINDOW;
    s->bought = 0;
    if (!fresh || blocked || s->visits_left <= 0) return 0;
    s->visits_left--;
    return 1;
}
