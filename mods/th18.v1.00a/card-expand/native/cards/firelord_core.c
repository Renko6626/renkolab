/* firelord_core.c —— 炎魔之王的纯逻辑（设计：docs/superpowers/specs/2026-09-06-firelord-design.md §2）。
 * 只用加减乘除与 sqrtss（-fno-math-errno 下的 __builtin_sqrtf）与 broken_core_core.h 的多项式 atan2 —— 不引 libm、零 x87。 */
#include <string.h>
#include "firelord_core.h"
#include "broken_core_core.h"      /* bc_atan2f：确定性 SSE 多项式 */

static float clampf(float v, float lo, float hi) { return v < lo ? lo : v > hi ? hi : v; }

void fl_summon(fl_state_t *s, float px, float py, float pz)
{
    memset(s, 0, sizeof *s);
    s->hp = FL_HP;
    s->x = clampf(px, FL_X_MIN, FL_X_MAX);
    s->y = clampf(py + FL_SUMMON_DY, FL_Y_MIN, FL_Y_MAX);
    s->z = pz;
}

void fl_spot_from_rand(uint32_t rnd, float *x, float *y)
{
    float u = (float)(rnd & 0xffffu) * (1.0f / 65536.0f);
    float v = (float)(rnd >> 16) * (1.0f / 65536.0f);
    *x = FL_X_MIN + (FL_X_MAX - FL_X_MIN) * u;
    *y = FL_Y_MIN + (FL_Y_MAX - FL_Y_MIN) * v;
}

uint32_t fl_pick_index(uint32_t rnd, uint32_t n) { return n ? rnd % n : 0; }

void fl_begin_move(fl_state_t *s, uint32_t rnd)
{
    s->sx = s->x; s->sy = s->y;
    fl_spot_from_rand(rnd, &s->tx, &s->ty);
    s->move_left = FL_MOVE_FRAMES;
    s->fire_pending = 1;
    s->moves++;
}

void fl_launch(fl_state_t *s, float tx, float ty)
{
    float dx = tx - s->x, dy = ty - s->y;
    float d = __builtin_sqrtf(dx * dx + dy * dy);
    uint32_t n = d > 0.0f ? (uint32_t)(d / FL_BALL_SPEED) + 1u : 1u;   /* 到点帧数（向上取整）；原地也至少飞 1 帧 */
    s->ball_active = 1;
    s->bx = s->x; s->by = s->y;
    s->bvx = dx / (float)n; s->bvy = dy / (float)n;                    /* 恰好 n 帧到点，不会飞过头 */
    s->bang = bc_atan2f(dy, dx);
    s->ball_left = n;
    s->ex = tx; s->ey = ty;
    s->shots++;
}

fl_step_t fl_step(fl_state_t *s, int blocked)
{
    fl_step_t r = { 0, 0, 0, 0, 0, 0 };
    if (blocked > 0) { s->hp -= blocked; s->blocked += (uint32_t)blocked; }
    s->frames++;

    /* 移动：smoothstep 插值，到位那帧开火 */
    if (s->move_left > 0) {
        float t = 1.0f - (float)(s->move_left - 1) / (float)FL_MOVE_FRAMES;   /* 最后一帧 t = 1 */
        float k = t * t * (3.0f - 2.0f * t);
        s->x = s->sx + (s->tx - s->sx) * k;
        s->y = s->sy + (s->ty - s->sy) * k;
        s->move_left--;
        if (s->move_left == 0 && s->fire_pending) { r.fire = 1; s->fire_pending = 0; }
    }
    if (s->frames % FL_PERIOD == 0) r.need_move = 1;

    /* 火球 */
    if (s->ball_active) {
        s->bx += s->bvx; s->by += s->bvy;
        s->ball_left--;
        if (s->ball_left == 0) {
            s->ball_active = 0;
            s->bx = s->ex; s->by = s->ey;
            s->blast_left = FL_BLAST_FRAMES;
            r.ball_arrived = 1;
        } else if (s->frames % FL_TRAIL_EVERY == 0) {
            r.trail = 1;
        }
    }
    if (s->blast_left > 0) { r.blast_dmg = FL_BLAST_DMG; s->blast_left--; }

    r.died = s->hp <= 0;
    return r;
}
