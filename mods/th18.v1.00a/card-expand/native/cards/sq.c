/* 黑桃 Q —— 道具自动回收范围大幅增加。
 * 抄 CardNitori（id 21）的 on_load：写玩家四个道具参数。Player__reset 的默认 {5,30,70,70}，Nitori {10,30,110,110}。
 * on_load 由 AbilityManager__notify_cards_on_load 在关卡开场（Player__reset 之后）调；商店买到后下一关生效，与 Nitori 同。 */
#include "sdk.h"

static int on_load(ce_card_t *c)
{
    (void)c;
    uint8_t *p = CE_PLAYER();
    if (!p) return 0;
    *(float *)(p + CE_PLAYER_ITEM_ATTRACT_SPD) = 10.0f;
    *(float *)(p + CE_PLAYER_ITEM_COLLECT_R)   = 30.0f;
    *(float *)(p + CE_PLAYER_ITEM_ATTRACT_RF)  = 250.0f;
    *(float *)(p + CE_PLAYER_ITEM_ATTRACT_RU)  = 250.0f;
    return 0;
}

CE_CARD(60, .on_load = on_load);
