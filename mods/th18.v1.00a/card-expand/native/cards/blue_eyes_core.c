/* blue_eyes_core.c —— 青眼白龙的纯逻辑（设计：docs/superpowers/specs/2026-09-04-blue-eyes-design.md §2）。 */
#include <string.h>
#include "blue_eyes_core.h"

void be_summon(be_state_t *s, float px, float py, float pz)
{
    memset(s, 0, sizeof *s);
    s->hp = BE_HP;
    s->x = px; s->y = py + BE_SUMMON_DY; s->z = pz;
}

void be_follow(be_state_t *s, float px, float py, float pz)       /* Tenshi 0x40e8c0：pos += (target - pos) * 0.04 */
{
    float ty = py + BE_FOLLOW_DY;
    s->x += (px - s->x) * BE_FOLLOW_LERP;
    s->y += (ty - s->y) * BE_FOLLOW_LERP;
    s->z += (pz - s->z) * BE_FOLLOW_LERP;
}

be_step_t be_step(be_state_t *s, int blocked)
{
    be_step_t r = { 0, 0, 0 };
    if (blocked > 0) { s->hp -= blocked; s->blocked += (uint32_t)blocked; }
    s->frames++;
    if (s->wave_left == 0 && s->frames % BE_WAVE_PERIOD == 0) {
        r.wave_start = 1;
        s->wave_left = BE_WAVE_FRAMES;
        s->waves++;
    }
    if (s->wave_left > 0) { r.beam_dmg = BE_WAVE_DMG; s->wave_left--; }
    r.died = s->hp <= 0;
    return r;
}
