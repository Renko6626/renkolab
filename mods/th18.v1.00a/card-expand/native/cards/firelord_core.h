/* firelord_core.h —— 炎魔之王拉格纳罗斯（id 72）的纯逻辑：生命 / 8 秒一次的随机移动 / 火球飞行与爆炸。
 * 不碰引擎、不产随机数（随机 dword 由调用方从游戏 RNG 取来喂进来），主机 make test-host 直接测。
 * 设计：docs/superpowers/specs/2026-09-06-firelord-design.md。 */
#pragma once
#include <stdint.h>

#define FL_HP             800
#define FL_POWER_COST     200      /* 2.00 火力 */
#define FL_POWER_GATE     300      /* 门槛 3.00：引擎 spend_power 永远保留 1.00，成本 + 一档才扣得实（零售 Tsukasa 同款：成本 1 档、门槛 2 档）*/
#define FL_RECHARGE       600      /* 10 s，与青眼同 */
#define FL_RADIUS         56.0f    /* 挡弹半径：本体约 128 px 高、翼展约 115 */
#define FL_PERIOD         480      /* 帧：每 8 s 一个周期（移动 → 到位开火）*/
#define FL_MOVE_FRAMES    40       /* 一次移动滑 40 帧（平滑 smoothstep）*/
#define FL_SUMMON_DY      (-96.0f) /* 召唤在自机上方 */
#define FL_X_MIN          (-160.0f) /* 随机落点范围：弹幕区上半（实体坐标：x 居中、y 从顶边起算）*/
#define FL_X_MAX          160.0f
#define FL_Y_MIN          64.0f
#define FL_Y_MAX          240.0f
#define FL_BALL_SPEED     8.0f     /* px / 帧：满场 ~600 px 也在 75 帧内到，远小于 480 的周期 ⇒ 场上最多一颗 */
#define FL_BLAST_FRAMES   8        /* 爆炸持续帧：每帧一个新伤害源（一个源对同一敌人只结算一次）*/
#define FL_BLAST_DMG      50       /* 每帧；8 × 50 = 400。50 ≤ 四个自机的每帧上限最小值（Sakuya 60）⇒ 不被钳 */
#define FL_BLAST_W        64.0f
#define FL_BLAST_H        64.0f
#define FL_TRAIL_EVERY    2        /* 飞行中每 2 帧留一个拖尾 */
#define FL_BAR_DY         76.0f    /* 血条中心相对本体中心的 y（本体下端约 +64）*/
#define FL_BAR_W          56.0f
#define FL_BAR_H          4.0f

typedef struct {
    int32_t  hp;
    uint32_t frames;        /* 召唤以来的帧数 */
    uint32_t blocked;       /* 累计挡弹 */
    uint32_t moves;         /* 已移动次数 */
    uint32_t shots;         /* 已投出火球数 */
    float    x, y, z;       /* 本体坐标 */
    float    sx, sy;        /* 本次移动的起点 */
    float    tx, ty;        /* 本次移动的终点 */
    uint32_t move_left;     /* 本次移动剩余帧；0 = 静止 */
    int      fire_pending;  /* 到位后要开火 */
    /* 火球（最多一颗）*/
    int      ball_active;
    float    bx, by;        /* 火球坐标 */
    float    bvx, bvy;      /* 每帧位移 */
    float    bang;          /* 飞行方向（弧度，0 = +x）*/
    uint32_t ball_left;     /* 剩余飞行帧 */
    float    ex, ey;        /* 落点 = 开火时记下的敌人坐标 */
    uint32_t blast_left;    /* 爆炸剩余帧 */
    /* ANM ids（引擎侧，core 不碰）*/
    uint32_t anm_id, ball_id, bar_bg_id, bar_id;
} fl_state_t;

typedef struct {
    int need_move;      /* 该抽随机落点了：调用方 fl_begin_move(s, ce_rand()) */
    int fire;           /* 到位了：调用方选目标 → fl_launch(s, tx, ty)（没目标就不调）*/
    int trail;          /* 本帧在 (bx, by) 留一个拖尾 */
    int ball_arrived;   /* 火球本帧到点：删火球 VM、起爆炸特效、放 0x2c */
    int blast_dmg;      /* 非 0 = 本帧在 (ex, ey) 放一个 blast_dmg 的 FL_BLAST_W×H 伤害源 */
    int died;
} fl_step_t;

void      fl_summon(fl_state_t *s, float px, float py, float pz);     /* 清零、hp = FL_HP、坐标 = (px, py + FL_SUMMON_DY) 钳进落点范围 */
fl_step_t fl_step(fl_state_t *s, int blocked);                          /* 每帧：扣血、计帧、移动插值、火球推进、爆炸计数 */
void      fl_begin_move(fl_state_t *s, uint32_t rnd);                   /* 用一个随机 dword 抽落点、开始滑动、到位后开火 */
void      fl_launch(fl_state_t *s, float tx, float ty);                 /* 朝 (tx, ty) 投火球：直线、FL_BALL_SPEED、到点即爆 */
void      fl_spot_from_rand(uint32_t rnd, float *x, float *y);          /* 低 16 位 → x、高 16 位 → y，均匀落在范围内 */
uint32_t  fl_pick_index(uint32_t rnd, uint32_t n);                      /* n > 0：rnd % n */
