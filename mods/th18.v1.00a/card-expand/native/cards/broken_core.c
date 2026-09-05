/* 破损核心（id 71）—— 装备卡：身边多一颗电球子机，每 BC_PERIOD 帧朝最近的敌人劈一道闪电（一道 120 = 连续 4 帧 × 30）。
 *
 * 子机走**零售装备卡机制**：`Player__allocate_option` 的 zPlayerOption（引擎管位置 / 聚焦位移 / 开店收起），
 * 长相 = ability.anm script88。与零售装备卡的两处不同：
 *   ① 子机指针存 `ce_state()` 而不是 card+0x54 —— 我们的对象是基类 0x54 字节，+0x54 在对象外；
 *   ② 不用 SHT shooterset 开火（那条链只在按住射击键时广播、而且弹要飞过去）。
 *
 * 闪电 = **定点伤害源 + 电弧特效**，两件独立的事：
 *   伤害：在目标坐标放一个 BC_HIT_W × BC_HIT_H 的矩形伤害源（`0x45dfa0`，Remilia / Tenshi / 青眼同款），
 *         寿命 BC_HIT_LIFE 帧、BC_DMG 伤害。它只罩住目标那一点 ⇒ 单体；一个伤害源对同一敌人只结算一次
 *         （`enm_compute_damage_sources` `0x45f0f0` 的 src+0x84 tag 守卫）⇒ 定量；走正常伤害管线
 *         （每帧上限 player+0x47984、计分、命中反馈）。
 *   特效：script89 电弧从电球拉到敌人（C 写 pos / rotation.z / scale.x），script90 火花在命中点。
 *
 * 纯逻辑在 broken_core_core.c（主机单测）。引擎一手 engine/card/th18/03-hooks.md §5、engine/player/th18/02-damage-sources.md；
 * 设计 docs/superpowers/specs/2026-09-05-broken-core-design.md；审计 AUDIT §U。 */
#include "sdk.h"
#include "broken_core_core.h"

#define BC_OPTION_OFFSET  0x18      /* 子机相对自机的横向偏移（非聚焦 / 聚焦同值）。零售：Marisa1 0x10、Alice 0x1c、Reimu1 0x30 */
#define BC_RETRY_FRAMES   60        /* 没拿到子机时的重试间隔（槽满 / 还没进关）*/
#define BC_HIT_W          32.0f     /* 钉在目标上的判定：罩住它的中心；4 帧里目标会挪一点，比第一版 24 放宽 */
#define BC_HIT_H          32.0f
#define BC_HIT_LIFE       2         /* 帧；同一敌人只结算一次（tag 守卫），2 帧是给结算留的余量 */
#define BC_SE             0x46      /* se_noise：电流 */
#define BC_BEAM_TEX_W     256.0f    /* 电弧贴图的宽（scale.x = 距离 / 它）*/

typedef struct {
    uint8_t   *option;              /* zPlayerOption*；0 = 还没有 */
    uint32_t   retry;               /* 重试倒计时 */
    bc_state_t st;
} bc_card_t;

/* 子机槽是引擎的公共资源：可能被回收、被别的卡拿走。每次用之前认领一次
 * （option+0xd0 是建它那张卡的 array_index，`Player__allocate_option` `0x40a790` 写的）。*/
static uint8_t *option_of(ce_card_t *c, bc_card_t *s)
{
    uint8_t *o = s->option;
    if (!o) return 0;
    if (*(int32_t *)(o + CE_OPT_IN_USE) == 0 ||
        *(uint32_t *)(o + CE_OPT_OWNER_INDEX) != *(uint32_t *)((uint8_t *)c + CE_CARD_ARRAY_INDEX)) {
        s->option = 0;
        return 0;
    }
    return o;
}

static uint8_t *make_option(ce_card_t *c, bc_card_t *s)
{
    if (!CE_PLAYER()) return 0;
    s->option = (uint8_t *)ce_allocate_option(c, BC_OPTION_OFFSET, CE_ANM_ABILITY_SCRIPT_BROKEN_CORE_ORB);
    ce_log("broken_core: option %s (ptr %08x, anm id %08x)", s->option ? "allocated" : "FAILED (pool full)",
           (unsigned)(uintptr_t)s->option, *(uint32_t *)((uint8_t *)c + CE_CARD_OPTION_ANM_ID));
    return s->option;
}

/* 收起电球：删掉子机的 ANM VM（零售在 `CardReimu1__operator_delete` `0x40ab20` 里做同一件事），
 * 并松开我们记的指针。槽本身由 `Player__repopulate_options_and_notify_cards` 统一回收。*/
static void drop_option(ce_card_t *c, bc_card_t *s)
{
    uint32_t *vm = (uint32_t *)((uint8_t *)c + CE_CARD_OPTION_ANM_ID);
    if (*vm) { ce_anm_delete(*vm); *vm = 0; }
    if (s) { s->option = 0; s->retry = 0; }
}

/* +0x18：`Player__repopulate_options_and_notify_cards` `0x45d5e0` 尾部广播（开局 / 火力档变 / 关店后）。
 * 池刚被重建过，所以这里无条件重新申请一个 —— 与零售装备卡一致。*/
static int on_power_level_change(ce_card_t *c)
{
    bc_card_t *s = ce_state(c, bc_card_t);
    if (s) make_option(c, s);
    return 0;
}

/* +0x20 / +0x4c：照 `CardReimu1____on_load__2` `0x40aab0` 与 `CardReimu1__method_4C` `0x40aad0`。*/
static void on_run_reset(ce_card_t *c)
{
    ce_card_flags(c) &= ~2u;                 /* 零售装备卡在这个槽里清的就是 bit1 */
    drop_option(c, ce_state(c, bc_card_t));
}

static int on_load(ce_card_t *c)
{
    on_run_reset(c);
    return 0;
}

/* +0x2c：AbilityManager 每帧（菜单 / 商店里不跑）。蓄满 + 有目标才开火；蓄满没目标就一直攒着。*/
static int on_tick_2(ce_card_t *c)
{
    bc_card_t *s = ce_state(c, bc_card_t);
    uint8_t *p = CE_PLAYER();
    uint8_t *em = CE_ENEMY_MGR();
    uint8_t *o;
    bc_aim_t aim;
    float ox, oy, tx, ty, pz, angle;
    uint32_t beam, spark;

    if (!s || !p) return 0;
    o = option_of(c, s);
    if (!o) {                                /* 关卡中途买到这张卡：广播可能还没来，自己补一个 */
        if (s->retry) { s->retry--; return 0; }
        s->retry = BC_RETRY_FRAMES;
        o = make_option(c, s);
        if (!o) return 0;
    }
    /* 上一道的后续伤害帧：每帧在钉住的目标坐标放一个新源（AUDIT U9：一源一算，所以要拆帧；U12：单帧 30 不撞上限）*/
    pz = ((const float *)(p + CE_PLAYER_X))[2];
    if (bc_hit_frame(&s->st)) {
        float center[3] = { s->st.tx, s->st.ty, pz };
        ce_damage_rect(center, 0.0f, BC_HIT_LIFE, BC_DMG_FRAME, BC_HIT_W, BC_HIT_H);
    }
    if (!bc_tick(&s->st) || !em) return 0;

    ox = (float)*(int32_t *)(o + CE_OPT_POS_X) * CE_SUBPIXEL_TO_PIXEL;
    oy = (float)*(int32_t *)(o + CE_OPT_POS_Y) * CE_SUBPIXEL_TO_PIXEL;
    bc_aim_reset(&aim);
    for (uint8_t **node = *(uint8_t ***)(em + CE_EM_ENEMY_LIST_HEAD); node; node = (uint8_t **)node[1]) {
        uint8_t *e = node[0];
        if (!e || (*(uint32_t *)(e + CE_ENEMY_FLAGS) & CE_ENEMY_FLAG_NO_LOCK)) continue;
        bc_aim_consider(&aim, ox, oy, *(float *)(e + CE_ENEMY_POS_X), *(float *)(e + CE_ENEMY_POS_Y));
    }
    if (!bc_aim_angle(&aim, &angle)) return 0;               /* 没目标：继续攒着（蓄满状态保持）*/
    tx = ox + aim.dx;
    ty = oy + aim.dy;

    /* 伤害：钉在目标上的小判定，从这一帧起连续 BC_HIT_FRAMES 帧每帧一个新源（本帧的这一个在这里放，其余由上面的 bc_hit_frame 放）。
     * angle 只影响判定框的朝向，给 0 就是轴对齐。 */
    bc_did_fire(&s->st, tx, ty);
    if (bc_hit_frame(&s->st)) {
        float center[3] = { tx, ty, pz };
        ce_damage_rect(center, 0.0f, BC_HIT_LIFE, BC_DMG_FRAME, BC_HIT_W, BC_HIT_H);
    }

    /* 特效：电弧从电球拉到敌人。贴图朝 +x 铺满 BC_BEAM_TEX_W，脚本里 anchor(1, 0) 左端对齐，
     * 所以 pos = 电球、rotation.z = 瞄准角、scale.x = 距离 / 贴图宽。第 0 帧的 scale 由这里写，
     * 之后脚本每帧 scale(%F0, 随机 %F1) 抖动 —— %F0 也在这里给。脚本不碰 rotate。 */
    beam = ce_anm_spawn(CE_ABILITY_ANM(), CE_ANM_ABILITY_SCRIPT_BROKEN_CORE_BEAM, 13);
    if (beam) {
        float sx = bc_aim_dist(&aim) * (1.0f / BC_BEAM_TEX_W);
        ce_anm_set_pos(beam, ox, oy, pz);
        ce_anm_set_rotation(beam, 0.0f, 0.0f, angle);
        ce_anm_set_scale(beam, sx, 1.0f);
        ce_anm_set_fvar(beam, 0, sx);
    }
    spark = ce_anm_spawn(CE_ABILITY_ANM(), CE_ANM_ABILITY_SCRIPT_BROKEN_CORE_SPARK, 13);
    if (spark) ce_anm_set_pos(spark, tx, ty, pz);
    ce_play_sound(BC_SE, ox);
    if (s->st.shots <= 3 || s->st.shots % 25 == 0)
        ce_log("broken_core: fire #%u at frame %u, orb (%.1f, %.1f) -> target (%.1f, %.1f) dist %.1f angle %.3f",
               s->st.shots, s->st.frames, ox, oy, tx, ty, bc_aim_dist(&aim), angle);
    return 0;
}

CE_CARD(71, .on_power_level_change = on_power_level_change, .on_tick_2 = on_tick_2,
            .on_load = on_load, .on_run_reset = on_run_reset);
