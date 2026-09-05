/* 破损核心（id 71）纯逻辑单测：开火节奏 / 挑最近的敌人 / atan2 近似。
 *   cc -std=c11 -Wall -Wextra -Werror -o t tests/test_broken_core_core.c cards/broken_core_core.c -lm && ./t */
#include <assert.h>
#include <math.h>
#include <stdio.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

#include "../cards/broken_core_core.h"

static int fails;
#define CHECK(cond, ...) do { if (!(cond)) { printf("FAIL %s:%d ", __FILE__, __LINE__); \
    printf(__VA_ARGS__); printf("\n"); fails++; } } while (0)

static void test_charge(void)
{
    bc_state_t s = {0, 0, 0, 0, 0.0f, 0.0f};
    for (int i = 1; i < BC_PERIOD; i++)
        CHECK(!bc_tick(&s), "帧 %d 就蓄满了", i);
    CHECK(bc_tick(&s), "第 %d 帧该蓄满", BC_PERIOD);
    CHECK(s.frames == (uint32_t)BC_PERIOD, "frames=%u", s.frames);

    /* 蓄满后没开火 → 一直保持蓄满 */
    for (int i = 0; i < 300; i++) CHECK(bc_tick(&s), "蓄满后第 %d 帧掉了", i);
    CHECK(s.shots == 0, "还没开火 shots=%u", s.shots);

    bc_did_fire(&s, 10.0f, 20.0f);
    CHECK(s.shots == 1 && s.tx == 10.0f && s.ty == 20.0f, "shots=%u", s.shots);
    /* 一道 = BC_HIT_FRAMES 帧伤害，之后不再放 */
    int hits = 0;
    for (int i = 0; i < BC_HIT_FRAMES + 5; i++) hits += bc_hit_frame(&s);
    CHECK(hits == BC_HIT_FRAMES, "伤害帧 %d ≠ %d", hits, BC_HIT_FRAMES);
    CHECK(BC_HIT_FRAMES * BC_DMG_FRAME == 120, "一道 = %d", BC_HIT_FRAMES * BC_DMG_FRAME);
    CHECK(!bc_tick(&s), "刚开完火不该马上又蓄满");
    for (int i = 1; i < BC_PERIOD; i++) bc_tick(&s);
    CHECK(bc_tick(&s), "第二发该蓄满了");
}

static void test_aim(void)
{
    bc_aim_t a;
    float ang;

    bc_aim_reset(&a);
    CHECK(!bc_aim_angle(&a, &ang), "没有候选却给出了角度");

    /* 射程外的不算 */
    bc_aim_reset(&a);
    bc_aim_consider(&a, 0.0f, 0.0f, BC_RANGE + 1.0f, 0.0f);
    CHECK(!bc_aim_angle(&a, &ang), "射程外的敌人被选中了");

    /* 边界：正好射程内 */
    bc_aim_reset(&a);
    bc_aim_consider(&a, 0.0f, 0.0f, BC_RANGE - 1.0f, 0.0f);
    CHECK(bc_aim_angle(&a, &ang), "射程内的敌人没选中");
    CHECK(fabsf(ang) < 1e-4f, "正右方角度应为 0，得到 %f", ang);

    /* 取最近的那个，与加入顺序无关 */
    bc_aim_reset(&a);
    bc_aim_consider(&a, 10.0f, 10.0f, 10.0f, -90.0f);   /* 距 100，正上方 */
    bc_aim_consider(&a, 10.0f, 10.0f, 60.0f, 10.0f);    /* 距 50，正右方 */
    bc_aim_consider(&a, 10.0f, 10.0f, 10.0f, 210.0f);   /* 距 200 */
    CHECK(bc_aim_angle(&a, &ang), "该有目标");
    CHECK(fabsf(ang) < 1e-4f, "该选正右方那个，得到 %f", ang);

    bc_aim_reset(&a);
    bc_aim_consider(&a, 10.0f, 10.0f, 60.0f, 10.0f);
    bc_aim_consider(&a, 10.0f, 10.0f, 10.0f, -30.0f);   /* 距 40，更近 */
    CHECK(bc_aim_angle(&a, &ang), "该有目标");
    CHECK(fabsf(ang + (float)M_PI / 2.0f) < 1e-4f, "该选正上方（−π/2），得到 %f", ang);
}

static void test_atan2(void)
{
    /* 与 libm 对拍：误差 < 2e-5 rad，且四个象限的符号一致 */
    float worst = 0.0f;
    for (int i = -720; i <= 720; i++) {
        float t = (float)i * (float)M_PI / 720.0f;
        for (float r = 1.0f; r <= 1000.0f; r *= 10.0f) {
            float x = r * cosf(t), y = r * sinf(t);
            float got = bc_atan2f(y, x), want = atan2f(y, x);
            float d = fabsf(got - want);
            if (d > (float)M_PI) d = 2.0f * (float)M_PI - d;   /* ±π 处的绕回 */
            if (d > worst) worst = d;
        }
    }
    CHECK(worst < 2e-5f, "atan2 最大误差 %g rad", worst);
    CHECK(bc_atan2f(0.0f, 0.0f) == 0.0f, "atan2(0,0) 该给 0");
    CHECK(fabsf(bc_atan2f(0.0f, -1.0f) - (float)M_PI) < 1e-4f, "atan2(0,-1) 该给 π");
    printf("  atan2 worst error %.2e rad\n", worst);
}

int main(void)
{
    test_charge();
    test_aim();
    test_atan2();
    printf(fails ? "broken_core_core: %d FAILED\n" : "broken_core_core: ok\n", fails);
    return fails ? 1 : 0;
}
