/* broken_core_core.c —— 破损核心的纯逻辑（设计：docs/superpowers/specs/2026-09-05-broken-core-design.md §3）。 */
#include "broken_core_core.h"

int bc_tick(bc_state_t *s)
{
    s->frames++;
    if (s->charge < BC_PERIOD) s->charge++;
    return s->charge >= BC_PERIOD;
}

void bc_did_fire(bc_state_t *s, float tx, float ty)
{
    s->charge = 0;
    s->shots++;
    s->tx = tx; s->ty = ty;
    s->hit_left = BC_HIT_FRAMES;
}

int bc_hit_frame(bc_state_t *s)
{
    if (s->hit_left == 0) return 0;
    s->hit_left--;
    return 1;
}

void bc_aim_reset(bc_aim_t *a)
{
    a->found = 0;
    a->best_d2 = BC_RANGE_SQ;      /* 一开始就是射程，超出射程的自然进不来 */
    a->dx = 0.0f;
    a->dy = 0.0f;
}

void bc_aim_consider(bc_aim_t *a, float ox, float oy, float ex, float ey)
{
    float dx = ex - ox, dy = ey - oy;
    float d2 = dx * dx + dy * dy;
    if (d2 < a->best_d2) {
        a->found = 1;
        a->best_d2 = d2;
        a->dx = dx;
        a->dy = dy;
    }
}

int bc_aim_angle(const bc_aim_t *a, float *out_angle)
{
    if (!a->found) return 0;
    *out_angle = bc_atan2f(a->dy, a->dx);
    return 1;
}
