/* 炎魔之王（id 72）纯逻辑单测：周期 / 移动插值 / 落点范围 / 火球到点 / 爆炸帧数 / 死亡。
 *   cc -std=c11 -Wall -Wextra -Werror -o t tests/test_firelord_core.c cards/firelord_core.c -lm && ./t */
#include <assert.h>
#include <math.h>
#include <stdio.h>

#include "../cards/firelord_core.h"

static int fails;
#define CHECK(cond, ...) do { if (!(cond)) { printf("FAIL %s:%d ", __FILE__, __LINE__); \
    printf(__VA_ARGS__); printf("\n"); fails++; } } while (0)

static void test_summon(void)
{
    fl_state_t s;
    fl_summon(&s, 0.0f, 300.0f, 0.5f);
    CHECK(s.hp == FL_HP, "hp=%d", s.hp);
    CHECK(s.x == 0.0f && s.y == 300.0f + FL_SUMMON_DY && s.z == 0.5f, "pos (%.1f, %.1f)", s.x, s.y);
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
    fl_summon(&s, 0.0f, 300.0f, 0.0f);
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
    fl_summon(&s, 0.0f, 200.0f, 0.0f);                  /* 本体在 (0, 104) */
    fl_launch(&s, 0.0f, 104.0f + 80.0f);                /* 正下方 80 px → 10 帧 + 1 */
    CHECK(s.ball_active && s.shots == 1, "launch");
    CHECK(s.ball_left == 11, "ball_left=%u", s.ball_left);
    CHECK(fabsf(s.bang - 1.5707964f) < 1e-3f, "朝下 = +π/2，得 %.4f", s.bang);
    int arrived = -1, trails = 0, dmg_frames = 0;
    for (int i = 1; i <= 40; i++) {
        fl_step_t st = fl_step(&s, 0);
        if (st.trail) trails++;
        if (st.ball_arrived) { arrived = i; CHECK(fabsf(s.bx) < 1e-4f && fabsf(s.by - 184.0f) < 1e-3f, "落点 (%.3f, %.3f)", s.bx, s.by); }
        if (st.blast_dmg) { CHECK(st.blast_dmg == FL_BLAST_DMG, "dmg=%d", st.blast_dmg); dmg_frames++; }
        if (i < 11) CHECK(s.ball_active, "帧 %d 火球提前没了", i);
    }
    CHECK(arrived == 11, "arrived at %d", arrived);
    CHECK(dmg_frames == FL_BLAST_FRAMES, "爆炸伤害帧 %d ≠ %d", dmg_frames, FL_BLAST_FRAMES);
    CHECK(trails == 5, "拖尾 %d（10 帧飞行、每 2 帧一个）", trails);
    CHECK(!s.ball_active && s.blast_left == 0, "结束后状态没清");
    /* 爆炸从到点那帧的**下一帧**开始（到点帧 blast_left 刚置上、本帧不结算） */
    fl_summon(&s, 0.0f, 200.0f, 0.0f);
    fl_launch(&s, 100.0f, 104.0f);                      /* 正右方：角度 0 */
    CHECK(fabsf(s.bang) < 1e-3f, "朝右 = 0，得 %.4f", s.bang);
    fl_step_t st = fl_step(&s, 0);
    CHECK(!st.ball_arrived && !st.blast_dmg, "第 1 帧不该到");
    /* 原地投（目标 = 自己）：至少飞 1 帧、不除零 */
    fl_launch(&s, s.x, s.y);
    CHECK(s.ball_left == 1 && s.bvx == 0.0f && s.bvy == 0.0f, "原地投 ball_left=%u", s.ball_left);
    st = fl_step(&s, 0);
    CHECK(st.ball_arrived, "原地投第 1 帧就到");
}

static void test_hp(void)
{
    fl_state_t s;
    fl_summon(&s, 0.0f, 300.0f, 0.0f);
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
    test_spot_range();
    test_period_and_move();
    test_fireball();
    test_hp();
    if (fails) { printf("%d FAIL\n", fails); return 1; }
    printf("test_firelord_core: OK\n");
    return 0;
}
