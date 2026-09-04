/* blue_eyes_core.h —— 青眼白龙的纯逻辑：生命 / 跟随 / 发波。不碰引擎，主机 make test-host 直接测。
 * 设计：docs/superpowers/specs/2026-09-04-blue-eyes-design.md §2。 */
#pragma once
#include <stdint.h>

#define BE_HP             2500
#define BE_WAVE_PERIOD    300      /* 帧：每 5 s 一波；第一波在召唤后第 300 帧 */
#define BE_WAVE_FRAMES    30
#define BE_WAVE_DMG       100      /* 每帧请求伤害；30 × 100 = 3000 名义值，实际受引擎每帧上限钳（不写 player+0x47984）*/
#define BE_RECHARGE       600
#define BE_RADIUS         48.0f
#define BE_FOLLOW_DY      (-80.0f)
#define BE_SUMMON_DY      (-100.0f)
#define BE_FOLLOW_LERP    0.04f
#define BE_BEAM_WIDTH     96.0f    /* 判定宽（用户 2026-09-04：大幅增宽；画面上的 Master Spark 贴图约 126 px 宽）*/
#define BE_MOUTH_DY       (-52.0f) /* 龙头（贴图顶端）相对龙中心的 y：256 × 0.45 / 2 ≈ 58，头尖略进一点 */

typedef struct {
    int32_t  hp;
    uint32_t frames;      /* 召唤以来的帧数 */
    uint32_t wave_left;   /* 本波剩余帧 */
    uint32_t waves;       /* 已发波数 */
    uint32_t blocked;     /* 累计挡弹 */
    float    x, y, z;     /* 龙坐标（玩家坐标系）*/
    uint32_t anm_id;      /* 龙 VM；0 = 没有 */
    uint32_t beam_id;     /* 当前光束 VM；0 = 没有 */
} be_state_t;

typedef struct { int wave_start; int beam_dmg; int died; } be_step_t;

void      be_summon(be_state_t *s, float px, float py, float pz);   /* 清零、hp = BE_HP、坐标 = (px, py + BE_SUMMON_DY, pz) */
void      be_follow(be_state_t *s, float px, float py, float pz);   /* 目标 (px, py + BE_FOLLOW_DY, pz)，lerp BE_FOLLOW_LERP */
be_step_t be_step(be_state_t *s, int blocked);                       /* 每帧：扣血、计帧、发波状态机 */
