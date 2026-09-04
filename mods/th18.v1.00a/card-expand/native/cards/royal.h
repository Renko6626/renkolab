/* 皇家同花顺 —— 黑桃 10/J/Q/K/A（58–62）共用的 ctor：买到第五张时触发隐藏效果。 */
#pragma once
#include "sdk.h"
int ce_royal_flush_ctor(ce_card_t *c);
void ce_royal_tick(ce_card_t *c);      /* 每帧（on_tick_2）：演出里延时放的音效 */
