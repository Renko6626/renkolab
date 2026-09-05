/* firelord_core.h —— 炎魔之王拉格纳罗斯（id 72）的纯逻辑：生命 / 8 秒一次的随机移动 / 火球飞行与爆炸。
 * 不碰引擎、不产随机数（随机 dword 由调用方从游戏 RNG 取来喂进来），主机 make test-host 直接测。
 * 设计：docs/superpowers/specs/2026-09-06-firelord-design.md。 */
#pragma once
#include <stdint.h>

#define FL_HP             800
#define FL_POWER_COST     200      /* 2.00 火力 */
#define FL_POWER_GATE     300      /* 门槛 3.00：引擎 spend_power 永远保留 1.00，成本 + 一档才扣得实（零售 Tsukasa 同款：成本 1 档、门槛 2 档）*/
#define FL_RECHARGE       600      /* 10 s，与青眼同 */
#define FL_RADIUS         28.0f    /* 挡弹半径：本体约 64 px 高（2026-09-06 用户：体积与半径都减半）*/
#define FL_PERIOD         480      /* 帧：每 8 s 一个周期（移动 → 到位开火）*/
#define FL_MOVE_FRAMES    60       /* 一次移动滑 60 帧（quintic ease-in-out：起步慢、中段快、落定慢）*/
#define FL_SUMMON_DY      (-64.0f) /* 召唤在自机上方（再钳进落点范围）*/
#define FL_X_MIN          (-160.0f) /* 随机落点范围：弹幕区**下 1/3**（实体坐标：x 居中、y 从顶边起算，区高 448 ⇒ 下 1/3 从 299 起）*/
#define FL_X_MAX          160.0f
#define FL_Y_MIN          300.0f
#define FL_Y_MAX          410.0f    /* 离底边留 38 px：本体半高 32 + 血条 */
#define FL_BOB_PERIOD     96        /* 帧：待命时上下呼吸浮动一个来回 */
#define FL_BOB_AMP        4.0f      /* px：浮动半幅（本体 64 px 高）*/
#define FL_BALL_SPEED     4.0f     /* px / 帧（2026-09-06 用户：放慢）：满场 ~600 px 也在 150 帧内到，仍远小于 480 的周期 ⇒ 场上最多一颗 */
#define FL_BLAST_FRAMES   12       /* 爆炸持续帧：每帧一个新伤害源（一个源对同一敌人只结算一次）。2026-09-06 用户：伤害加大 → 8 → 12 帧 */
#define FL_BLAST_DMG      50       /* 每帧；12 × 50 = 600。50 ≤ 四个自机的每帧上限最小值（Sakuya 60）⇒ 不被钳；加帧数而不是加单帧值就是为了这个 */
#define FL_BLAST_W        96.0f    /* 杀伤范围 64 → 96（2026-09-06 用户）*/
#define FL_BLAST_H        96.0f
#define FL_PARTICLES      2        /* 飞行中每帧撒几颗橙白粒子（script95，各自随机飘散）*/
#define FL_BURST          10       /* 落地那帧撒几颗火星（script96）*/
#define FL_AURA           2        /* 常态：本体每帧撒几颗身体火焰（script97，与火球粒子同量）*/
#define FL_SHAKE_TIME     14       /* 震屏帧数（ECL setScreenShake 同款机制；零售 boss 死亡量级更大）*/
#define FL_SHAKE_START    5        /* 起始强度（相机像素偏移）*/
#define FL_SHAKE_END      0
#define FL_TRAIL_EVERY    2        /* 飞行中每 2 帧留一个拖尾 */
#define FL_BAR_DY         40.0f    /* 血条中心相对本体中心的 y（本体下端约 +32）*/
#define FL_BAR_W          40.0f
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

/* 呼吸浮动：画面 y = s->y + 它（判定 / 血条一起跟）。三角相位 → smoothstep 折成来回 = 一条 C¹ 连续的近似正弦，不引 libm。
 * frames = 0（召唤那帧）在最低点 −AMP，之后先上浮。**static inline 的理由同 bc_atan2f**：i386 ABI 返回 float 走 st0（flds），
 * 内联掉才守得住 make dllx87 的「零 x87」。*/
static inline float fl_bob_dy(const fl_state_t *s)
{
    uint32_t ph = s->frames % FL_BOB_PERIOD;
    float t = (float)ph / ((float)FL_BOB_PERIOD * 0.5f);   /* [0, 2) */
    if (t > 1.0f) t = 2.0f - t;                            /* 三角波 */
    float k = t * t * (3.0f - 2.0f * t);                   /* smoothstep：两端速度为 0 */
    return (k * 2.0f - 1.0f) * FL_BOB_AMP;                 /* [−AMP, +AMP] */
}
