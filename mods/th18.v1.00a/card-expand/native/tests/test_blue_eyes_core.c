/* test_blue_eyes_core.c —— blue_eyes_core.c 的主机单测（make test-host）。 */
#include <stdio.h>
#include <math.h>
#include "../cards/blue_eyes_core.h"

static int s_fail, s_pass;
#define CHECK(cond) do { if (cond) ++s_pass; else { ++s_fail; printf("  FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); } } while (0)

static void test_summon_and_follow(void)
{
    be_state_t s;
    be_summon(&s, 10.0f, 400.0f, 0.0f);
    CHECK(s.hp == BE_HP && s.frames == 0 && s.wave_left == 0 && s.waves == 0 && s.anm_id == 0);
    CHECK(s.x == 10.0f && s.y == 300.0f && s.z == 0.0f);
    be_follow(&s, 110.0f, 400.0f, 0.0f);                 /* 目标 (110, 320)：x 走 4，y 走 0.8 */
    CHECK(fabsf(s.x - 14.0f) < 1e-4f);
    CHECK(fabsf(s.y - 300.8f) < 1e-4f);
    for (int i = 0; i < 2000; ++i) be_follow(&s, 110.0f, 400.0f, 0.0f);
    CHECK(fabsf(s.x - 110.0f) < 0.01f && fabsf(s.y - 320.0f) < 0.01f);   /* 收敛到目标 */
}

static void test_hp_and_death(void)
{
    be_state_t s;
    be_summon(&s, 0, 0, 0);
    be_step_t r = be_step(&s, 7);
    CHECK(s.hp == BE_HP - 7 && s.blocked == 7 && !r.died && !r.wave_start && r.beam_dmg == 0);
    r = be_step(&s, BE_HP);                              /* 一帧挡满 → 死 */
    CHECK(r.died && s.hp <= 0);
}

static void test_wave_timing(void)
{
    be_state_t s;
    be_summon(&s, 0, 0, 0);
    int starts = 0, dmg = 0;
    for (int f = 1; f <= BE_WAVE_PERIOD - 1; ++f) {
        be_step_t r = be_step(&s, 0);
        starts += r.wave_start; dmg += r.beam_dmg;
    }
    CHECK(starts == 0 && dmg == 0);                      /* 前 299 帧没波 */
    be_step_t r = be_step(&s, 0);                        /* 第 300 帧 */
    CHECK(r.wave_start == 1 && r.beam_dmg == BE_WAVE_DMG && s.waves == 1 && s.wave_left == BE_WAVE_FRAMES - 1);
    dmg = r.beam_dmg;
    for (int f = 0; f < BE_WAVE_FRAMES - 1; ++f) { r = be_step(&s, 0); CHECK(!r.wave_start); dmg += r.beam_dmg; }
    CHECK(dmg == BE_WAVE_FRAMES * BE_WAVE_DMG);         /* 一波共 3000 */
    r = be_step(&s, 0);
    CHECK(r.beam_dmg == 0 && s.wave_left == 0);          /* 第 31 帧停 */
    for (unsigned f = s.frames; f < 2 * BE_WAVE_PERIOD - 1; ++f) { r = be_step(&s, 0); CHECK(!r.wave_start); }
    r = be_step(&s, 0);
    CHECK(r.wave_start == 1 && s.waves == 2 && s.frames == 2 * BE_WAVE_PERIOD);   /* 第 600 帧第二波 */
}

int main(void)
{
    test_summon_and_follow();
    test_hp_and_death();
    test_wave_timing();
    printf("test_blue_eyes_core: %d pass, %d fail\n", s_pass, s_fail);
    return s_fail != 0;
}
