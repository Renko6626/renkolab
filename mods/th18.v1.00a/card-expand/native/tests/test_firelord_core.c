/* 炎魔之王（id 72）纯逻辑单测：周期 / 移动插值 / 落点范围 / 火球到点 / 爆炸帧数 / 死亡。
 *   cc -std=c11 -Wall -Wextra -Werror -o t tests/test_firelord_core.c cards/firelord_core.c -lm && ./t */
#include <assert.h>
#include <math.h>
#include <stdio.h>

#include "../cards/firelord_core.h"

static int fails;
#define CHECK(cond, ...) do { if (!(cond)) { printf("FAIL %s:%d ", __FILE__, __LINE__); \
    printf(__VA_ARGS__); printf("\n"); fails++; } } while (0)

/* 走完登场：FL_INTRO_FRAMES 帧聚气、最后一帧 appear；返回 appear 那帧的结果。之后 frames 仍为 0。*/
static fl_step_t run_intro(fl_state_t *s)
{
    fl_step_t st = { 0, 0, 0, 0, 0, 0, 0, 0, 0 };
    for (int i = 0; i < FL_INTRO_FRAMES; i++) {
        st = fl_step(s, 0);
        CHECK(st.gather, "登场第 %d 帧该聚气", i + 1);
        CHECK(!st.need_move && !st.fire && !st.died, "登场第 %d 帧不该动 / 开火 / 死", i + 1);
        if (i + 1 < FL_INTRO_FRAMES) CHECK(!st.appear, "第 %d 帧就出现了", i + 1);
    }
    CHECK(st.appear, "第 %d 帧该出现", FL_INTRO_FRAMES);
    CHECK(s->frames == 0 && s->intro_left == 0, "登场后 frames=%u intro_left=%u", s->frames, s->intro_left);
    return st;
}

static void test_intro(void)
{
    fl_state_t s;
    fl_summon(&s, 0.0f, 400.0f, 0.0f);
    CHECK(s.intro_left == FL_INTRO_FRAMES, "intro_left=%u", s.intro_left);
    fl_step_t st = fl_step(&s, 500);                     /* 聚气中挡弹数被忽略（C 也不会调消弹）*/
    CHECK(s.hp == FL_HP && st.gather && !st.appear, "聚气第 1 帧 hp=%d", s.hp);
    fl_summon(&s, 0.0f, 400.0f, 0.0f);
    run_intro(&s);
    CHECK(s.rings_left == FL_INTRO_RINGS - 1, "rings_left=%u", s.rings_left);
    int rings = 0, first = -1, last = -1;
    for (int i = 1; i <= FL_RING_GAP * FL_INTRO_RINGS + 5; i++) {
        st = fl_step(&s, 0);
        if (st.ring) { rings++; if (first < 0) first = i; last = i; }
    }
    CHECK(rings == FL_INTRO_RINGS - 1, "补圈 %d ≠ %d", rings, FL_INTRO_RINGS - 1);
    CHECK(first == FL_RING_GAP && last == 2 * FL_RING_GAP, "补圈时刻 %d / %d（应为 %d / %d）", first, last, FL_RING_GAP, 2 * FL_RING_GAP);
    CHECK(s.rings_left == 0, "rings_left=%u", s.rings_left);
}

static void test_summon(void)
{
    fl_state_t s;
    fl_summon(&s, 0.0f, 400.0f, 0.5f);
    CHECK(s.hp == FL_HP, "hp=%d", s.hp);
    CHECK(s.x == 0.0f && s.y == 400.0f + FL_SUMMON_DY && s.z == 0.5f, "pos (%.1f, %.1f)", s.x, s.y);
    fl_summon(&s, -300.0f, 20.0f, 0.0f);                 /* 自机贴边 / 贴顶：召唤点钳进范围 */
    CHECK(s.x == FL_X_MIN && s.y == FL_Y_MIN, "clamp (%.1f, %.1f)", s.x, s.y);
    CHECK(!s.ball_active && s.move_left == 0 && s.blast_left == 0, "state not clean");
}

static void test_spot_range(void)
{
    float x, y;
    uint32_t r = 0x12345678u;
    for (int i = 0; i < 2000; i++) {
        r = r * 1664525u + 1013904223u;
        fl_spot_from_rand(r, &x, &y);
        CHECK(x >= FL_X_MIN && x < FL_X_MAX, "x=%.2f", x);
        CHECK(y >= FL_Y_MIN && y < FL_Y_MAX, "y=%.2f", y);
    }
    fl_spot_from_rand(0, &x, &y);
    CHECK(x == FL_X_MIN && y == FL_Y_MIN, "rnd 0 → 左上角");
    fl_spot_from_rand(0xffffffffu, &x, &y);
    CHECK(x < FL_X_MAX && y < FL_Y_MAX && x > FL_X_MAX - 0.01f && y > FL_Y_MAX - 0.01f, "rnd max → 右下角内侧 (%.3f, %.3f)", x, y);
    CHECK(fl_pick_index(7, 3) == 1 && fl_pick_index(9, 1) == 0 && fl_pick_index(5, 0) == 0, "pick_index");
}

static void test_period_and_move(void)
{
    fl_state_t s;
    fl_summon(&s, 0.0f, 400.0f, 0.0f);
    run_intro(&s);
    fl_step_t st;
    for (int i = 1; i < FL_PERIOD; i++) {
        st = fl_step(&s, 0);
        CHECK(!st.need_move && !st.fire, "帧 %d 不该动 / 开火", i);
    }
    st = fl_step(&s, 0);
    CHECK(st.need_move, "第 %d 帧该抽落点", FL_PERIOD);
    float x0 = s.x, y0 = s.y;
    fl_begin_move(&s, 0x8000c000u);                     /* u = 0.75、v = 0.5 */
    CHECK(s.move_left == FL_MOVE_FRAMES && s.moves == 1, "move_left=%u", s.move_left);
    float want_x = FL_X_MIN + (FL_X_MAX - FL_X_MIN) * 0.75f, want_y = FL_Y_MIN + (FL_Y_MAX - FL_Y_MIN) * 0.5f;
    CHECK(fabsf(s.tx - want_x) < 1e-3f && fabsf(s.ty - want_y) < 1e-3f, "target (%.2f, %.2f)", s.tx, s.ty);
    float prev = 0.0f;
    for (int i = 1; i <= FL_MOVE_FRAMES; i++) {
        st = fl_step(&s, 0);
        float prog = (s.x - x0) / (want_x - x0);
        CHECK(prog >= prev - 1e-5f && prog <= 1.0f + 1e-5f, "帧 %d 进度倒退 %.4f < %.4f", i, prog, prev);
        prev = prog;
        if (i < FL_MOVE_FRAMES) CHECK(!st.fire, "帧 %d 还没到位就开火", i);
    }
    CHECK(st.fire, "到位那帧该开火");
    CHECK(fabsf(s.x - want_x) < 1e-3f && fabsf(s.y - want_y) < 1e-3f, "终点 (%.3f, %.3f) ≠ (%.3f, %.3f)", s.x, s.y, want_x, want_y);
    (void)y0;
    st = fl_step(&s, 0);
    CHECK(!st.fire && s.move_left == 0, "到位后不该再开火");
    /* 第二个周期照样来 */
    while (s.frames % FL_PERIOD != 0) st = fl_step(&s, 0);
    CHECK(st.need_move, "第二周期该再抽落点（frames=%u）", s.frames);
}

static void test_fireball(void)
{
    fl_state_t s;
    fl_summon(&s, 0.0f, 400.0f, 0.0f);                  /* 本体在 (0, 336) */
    run_intro(&s);
    fl_launch(&s, 0.0f, 336.0f + 80.0f);                /* 正下方 80 px → ⌊80 / 速度⌋ + 1 帧 */
    const uint32_t want_n = (uint32_t)(80.0f / FL_BALL_SPEED) + 1u;
    int want_trails = 0;
    for (uint32_t f = 1; f < want_n; f++) if (f % FL_TRAIL_EVERY == 0) want_trails++;
    CHECK(s.ball_active && s.shots == 1, "launch");
    CHECK(s.ball_left == want_n, "ball_left=%u ≠ %u", s.ball_left, want_n);
    CHECK(fabsf(s.bang - 1.5707964f) < 1e-3f, "朝下 = +π/2，得 %.4f", s.bang);
    int arrived = -1, trails = 0, dmg_frames = 0;
    for (int i = 1; i <= (int)want_n + FL_BLAST_FRAMES + 5; i++) {
        fl_step_t st = fl_step(&s, 0);
        if (st.trail) trails++;
        if (st.ball_arrived) { arrived = i; CHECK(fabsf(s.bx) < 1e-4f && fabsf(s.by - 416.0f) < 1e-3f, "落点 (%.3f, %.3f)", s.bx, s.by); }
        if (st.blast_dmg) { CHECK(st.blast_dmg == FL_BLAST_DMG, "dmg=%d", st.blast_dmg); dmg_frames++; }
        if (i < (int)want_n) CHECK(s.ball_active, "帧 %d 火球提前没了", i);
    }
    CHECK(arrived == (int)want_n, "arrived at %d ≠ %u", arrived, want_n);
    CHECK(dmg_frames == FL_BLAST_FRAMES, "爆炸伤害帧 %d ≠ %d", dmg_frames, FL_BLAST_FRAMES);
    CHECK(trails == want_trails, "拖尾 %d ≠ %d（%u 帧飞行、每 %d 帧一个）", trails, want_trails, want_n - 1, FL_TRAIL_EVERY);
    CHECK(!s.ball_active && s.blast_left == 0, "结束后状态没清");
    /* 爆炸从到点那帧的**下一帧**开始（到点帧 blast_left 刚置上、本帧不结算） */
    fl_summon(&s, 0.0f, 400.0f, 0.0f);
    run_intro(&s);
    fl_launch(&s, 100.0f, 336.0f);                      /* 正右方：角度 0 */
    CHECK(fabsf(s.bang) < 1e-3f, "朝右 = 0，得 %.4f", s.bang);
    fl_step_t st = fl_step(&s, 0);
    CHECK(!st.ball_arrived && !st.blast_dmg, "第 1 帧不该到");
    /* 原地投（目标 = 自己）：至少飞 1 帧、不除零 */
    fl_launch(&s, s.x, s.y);
    CHECK(s.ball_left == 1 && s.bvx == 0.0f && s.bvy == 0.0f, "原地投 ball_left=%u", s.ball_left);
    st = fl_step(&s, 0);
    CHECK(st.ball_arrived, "原地投第 1 帧就到");
}

static void test_bob(void)
{
    fl_state_t s;
    fl_summon(&s, 0.0f, 400.0f, 0.0f);
    run_intro(&s);
    float prev = fl_bob_dy(&s), lo = prev, hi = prev, maxstep = 0.0f;
    CHECK(prev == -FL_BOB_AMP, "第 0 帧该在最低点，得 %.3f", prev);
    for (int i = 1; i <= 3 * FL_BOB_PERIOD; i++) {
        fl_step(&s, 0);
        float b = fl_bob_dy(&s);
        CHECK(b >= -FL_BOB_AMP - 1e-4f && b <= FL_BOB_AMP + 1e-4f, "帧 %d 越幅 %.3f", i, b);
        float d = fabsf(b - prev);
        if (d > maxstep) maxstep = d;
        if (b < lo) lo = b;
        if (b > hi) hi = b;
        prev = b;
    }
    CHECK(fabsf(lo + FL_BOB_AMP) < 1e-3f && fabsf(hi - FL_BOB_AMP) < 1e-3f, "幅度 [%.3f, %.3f]", lo, hi);
    CHECK(maxstep < 2.0f * FL_BOB_AMP * 1.5f / (FL_BOB_PERIOD / 2) + 1e-3f, "最大单帧位移 %.3f 过大（不平滑）", maxstep);
    /* 周期：整周期后回到起点 */
    fl_summon(&s, 0.0f, 400.0f, 0.0f);
    run_intro(&s);
    for (int i = 0; i < FL_BOB_PERIOD; i++) fl_step(&s, 0);
    CHECK(fabsf(fl_bob_dy(&s) + FL_BOB_AMP) < 1e-4f, "一个周期后不在起点：%.3f", fl_bob_dy(&s));
}

static void test_hp(void)
{
    fl_state_t s;
    fl_summon(&s, 0.0f, 400.0f, 0.0f);
    run_intro(&s);
    fl_step_t st = fl_step(&s, 300);
    CHECK(s.hp == FL_HP - 300 && s.blocked == 300 && !st.died, "hp=%d", s.hp);
    st = fl_step(&s, FL_HP);                            /* 一帧挡了超过剩余（引擎按 max_count = hp 会截断，这里测下限）*/
    CHECK(st.died && s.hp <= 0, "该死了 hp=%d", s.hp);
    st = fl_step(&s, 0);
    CHECK(st.died, "死后仍报 died");
}

int main(void)
{
    test_summon();
    test_intro();
    test_spot_range();
    test_period_and_move();
    test_fireball();
    test_bob();
    test_hp();
    if (fails) { printf("%d FAIL\n", fails); return 1; }
    printf("test_firelord_core: OK\n");
    return 0;
}
