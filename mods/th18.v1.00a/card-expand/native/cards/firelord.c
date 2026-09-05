/* 炎魔之王拉格纳罗斯（id 72）—— 主动卡：按 C 消耗 2.00 火力，召唤一尊不跟随自机的炎魔。FL_HP 点生命替玩家挡子弹
 * （每挡一发 −1，被挡的弹照炸弹消弹变点道具），每 FL_PERIOD 帧抽一个随机落点滑过去，到位那帧向场上**随机一个**敌人
 * 投一颗火球（飞行物，飞向开火时记下的坐标），落地爆炸：连续 FL_BLAST_FRAMES 帧、每帧一个 FL_BLAST_W×H 的矩形伤害源。
 * 生命归零 → 死亡动画、结束；过关 / 局末消失。火力 < FL_POWER_GATE 拒绝（引擎永远保留 1.00，成本 + 一档才扣得实）。
 *
 * 零售原型：扣火力三步 = CardTsukasa__c_press（0x410e60：门槛 → spend_power → repopulate）；挡弹 = Tenshi 要石；
 * 伤害源 = Remilia 脉冲 / 青眼 / 破损核心同一个原语。随机 = 游戏自己的 REPLAY_SAFE_RNG。
 * 纯逻辑在 firelord_core.c（主机单测）；引擎调用是 sdk.h 的薄包装（AUDIT §V）。
 * 设计：docs/superpowers/specs/2026-09-06-firelord-design.md */
#include "sdk.h"
#include "firelord_core.h"

#define FL_COLOR_IDLE 0xffffffffu
#define FL_COLOR_HIT  0xffff8040u          /* 挡到弹那帧染橙（青眼是 Tenshi 的蓝 0xff0080ff）*/
#define FL_SE_SUMMON  CE_SE_RELEASE         /* 0x4d 发动音，语音 FIRELORD_SUMMON 叠在上面 */
#define FL_SE_BLAST   CE_SE_BOMB            /* 0x2c 火球落地 */
#define FL_SE_DEATH   0x29                  /* Tenshi 要石收场音（青眼同款）*/
#define FL_BAR_HIGH   0xffff9030u           /* > 50％ 橙 */
#define FL_BAR_MID    0xffffd040u           /* > 20％ 黄 */
#define FL_BAR_LOW    0xffff4040u           /* 红 */

/* 血条：复用青眼的两个 drawRect 根脚本（86 底槽 / 87 填充），C 每帧写 pos / scale / color（AUDIT O29k 同款）。*/
static void bar_update(fl_state_t *s)
{
    float ratio = s->hp > 0 ? (float)s->hp / (float)FL_HP : 0.0f;
    float w = FL_BAR_W * ratio, y = s->y + fl_bob_dy(s) + FL_BAR_DY;   /* 血条跟着呼吸浮动 */
    ce_anm_set_pos(s->bar_bg_id, s->x, y, s->z);
    ce_anm_set_scale(s->bar_bg_id, FL_BAR_W + 4.0f, FL_BAR_H + 4.0f);
    ce_anm_set_pos(s->bar_id, s->x - (FL_BAR_W - w) * 0.5f, y, s->z);
    ce_anm_set_scale(s->bar_id, w > 0.0f ? w : 0.0f, FL_BAR_H);
    ce_anm_set_color(s->bar_id, ratio > 0.5f ? FL_BAR_HIGH : ratio > 0.2f ? FL_BAR_MID : FL_BAR_LOW);
}

static void bar_destroy(fl_state_t *s, int fade)
{
    if (fade) { ce_anm_interrupt(s->bar_bg_id, 1); ce_anm_interrupt(s->bar_id, 1); }
    else      { ce_anm_delete(s->bar_bg_id);       ce_anm_delete(s->bar_id); }
    s->bar_bg_id = 0; s->bar_id = 0;
}

static float player_x(void) { uint8_t *p = CE_PLAYER(); return p ? *(float *)(p + CE_PLAYER_X) : 0.0f; }

static int refuse(const char *why)
{
    ce_play_sound(CE_SE_INVALID, player_x());
    ce_log("firelord: refused (%s)", why);
    return CE_ACTIVATE_REFUSED;
}

static void dismiss(ce_card_t *c, const char *why)
{
    fl_state_t *s = ce_state(c, fl_state_t);
    if (!s) return;
    if (s->anm_id || s->ball_id || s->bar_id) {
        ce_anm_delete(s->anm_id);
        ce_anm_delete(s->ball_id);
        bar_destroy(s, 0);
        ce_log("firelord: dismissed (%s) hp %d after %u frames, %u moves, %u shots, %u blocked",
               why, s->hp, s->frames, s->moves, s->shots, s->blocked);
    }
    s->anm_id = 0; s->ball_id = 0; s->hp = 0; s->ball_active = 0; s->blast_left = 0;
}

/* 场上随机一个可锁定的敌人（与破损核心同一套过滤：EnemyManager+0x18c 链表、跳过 +0x635c & 0xc000021）。
 * 两遍遍历：先数、再按游戏 RNG 抽的下标取坐标。只在本帧读，不缓存 enemy 指针。返回 0 = 没目标。*/
static int pick_random_enemy(float *tx, float *ty, uint32_t *out_n, uint32_t *out_idx)
{
    uint8_t *em = CE_ENEMY_MGR();
    uint32_t n = 0, idx, i = 0;
    if (!em) return 0;
    for (uint8_t **node = *(uint8_t ***)(em + CE_EM_ENEMY_LIST_HEAD); node; node = (uint8_t **)node[1]) {
        uint8_t *e = node[0];
        if (e && !(*(uint32_t *)(e + CE_ENEMY_FLAGS) & CE_ENEMY_FLAG_NO_LOCK)) n++;
    }
    if (!n) return 0;
    idx = fl_pick_index(ce_rand(), n);
    for (uint8_t **node = *(uint8_t ***)(em + CE_EM_ENEMY_LIST_HEAD); node; node = (uint8_t **)node[1]) {
        uint8_t *e = node[0];
        if (!e || (*(uint32_t *)(e + CE_ENEMY_FLAGS) & CE_ENEMY_FLAG_NO_LOCK)) continue;
        if (i++ == idx) {
            *tx = *(float *)(e + CE_ENEMY_POS_X);
            *ty = *(float *)(e + CE_ENEMY_POS_Y);
            *out_n = n; *out_idx = idx;
            return 1;
        }
    }
    return 0;
}

static int on_activate(ce_card_t *c)
{
    uint8_t *p = CE_PLAYER();
    if (!p) return refuse("no player");
    int power = CE_CURRENT_POWER();
    if (power < FL_POWER_GATE) return refuse("power too low");
    fl_state_t *s = ce_state(c, fl_state_t);
    if (!s) return refuse("no state slot");

    const float *pp = (const float *)(p + CE_PLAYER_X);
    fl_summon(s, pp[0], pp[1], pp[2]);
    s->anm_id = ce_anm_spawn(CE_ABILITY_ANM(), CE_ANM_ABILITY_SCRIPT_FIRELORD_BODY, 13);
    if (!s->anm_id) return refuse("body anm failed");
    ce_anm_set_pos(s->anm_id, s->x, s->y + fl_bob_dy(s), s->z);
    s->bar_bg_id = ce_anm_spawn(CE_ABILITY_ANM(), CE_ANM_ABILITY_SCRIPT_BLUE_EYES_BAR_BG, 13);
    s->bar_id    = ce_anm_spawn(CE_ABILITY_ANM(), CE_ANM_ABILITY_SCRIPT_BLUE_EYES_BAR, 13);
    bar_update(s);

    /* 照 Tsukasa：spend_power → 无条件 repopulate（扣 2 档时档数必变；repopulate 顺手广播 on_power_level_change）*/
    int level_changed = ce_spend_power(FL_POWER_COST);
    ce_repopulate_options();
    ce_play_sound(FL_SE_SUMMON, pp[0]);
    ce_play_voice(FIRELORD_SUMMON, pp[0]);
    ce_log("firelord: summoned, power %d -> %d (level changed %d), hp %d, anm id %08x, pos (%.1f, %.1f)",
           power, CE_CURRENT_POWER(), level_changed, s->hp, s->anm_id, s->x, s->y);
    return 1;
}

static int on_active_tick(ce_card_t *c, uint32_t elapsed)
{
    fl_state_t *s = ce_state(c, fl_state_t);
    uint8_t *p = CE_PLAYER();
    if (!s || !p) return 0;
    if (!ce_anm_get_vm(s->anm_id)) {                       /* 引擎把 VM 收掉了（O29h 同款）：本体没了就结束 */
        ce_log("firelord: body vm gone at frame %u", s->frames);
        s->anm_id = 0;
        ce_anm_delete(s->ball_id); s->ball_id = 0;
        bar_destroy(s, 0);
        return 0;
    }
    float pz = ((const float *)(p + CE_PLAYER_X))[2];
    float pos[3] = { s->x, s->y + fl_bob_dy(s), s->z };      /* 判定跟画面：呼吸浮动一起算 */
    int blocked = s->hp > 0 ? ce_cancel_radius(pos, FL_RADIUS, s->hp, 0) : 0;
    ce_anm_set_color(s->anm_id, blocked ? FL_COLOR_HIT : FL_COLOR_IDLE);

    fl_step_t st = fl_step(s, blocked);
    ce_anm_set_pos(s->anm_id, s->x, s->y + fl_bob_dy(s), s->z);   /* 逻辑位置 (x, y) + 呼吸浮动 */
    bar_update(s);

    if (st.need_move) {
        fl_begin_move(s, ce_rand());
        ce_log("firelord: move #%u at frame %u: (%.1f, %.1f) -> (%.1f, %.1f)", s->moves, s->frames, s->sx, s->sy, s->tx, s->ty);
    }
    if (st.fire) {
        float tx, ty; uint32_t n, idx;
        if (pick_random_enemy(&tx, &ty, &n, &idx)) {
            fl_launch(s, tx, ty);
            ce_anm_delete(s->ball_id);                     /* 理论上到不了这（周期 ≫ 飞行时间），保险 */
            s->ball_id = ce_anm_spawn(CE_ABILITY_ANM(), CE_ANM_ABILITY_SCRIPT_FIRELORD_FIREBALL, 13);
            ce_play_voice(FIRELORD_ATTACK, s->x);
            ce_log("firelord: shot #%u at frame %u: enemy %u/%u at (%.1f, %.1f), %u frames of flight, angle %.3f",
                   s->shots, s->frames, idx, n, tx, ty, s->ball_left, s->bang);
        } else {
            ce_log("firelord: no target at frame %u (move #%u done)", s->frames, s->moves);
        }
    }
    if (s->ball_active && s->ball_id) {                    /* 火球：pos / rotation 归 C，scale 归脚本（脉动）*/
        ce_anm_set_pos(s->ball_id, s->bx, s->by, pz);
        ce_anm_set_rotation(s->ball_id, 0.0f, 0.0f, s->bang);
    }
    if (st.trail) {
        uint32_t t = ce_anm_spawn(CE_ABILITY_ANM(), CE_ANM_ABILITY_SCRIPT_FIRELORD_TRAIL, 13);
        if (t) ce_anm_set_pos(t, s->bx, s->by, pz);
    }
    if (st.ball_arrived) {
        ce_anm_delete(s->ball_id); s->ball_id = 0;
        uint32_t b = ce_anm_spawn(CE_ABILITY_ANM(), CE_ANM_ABILITY_SCRIPT_FIRELORD_BLAST, 13);
        if (b) ce_anm_set_pos(b, s->ex, s->ey, pz);
        ce_play_sound(FL_SE_BLAST, s->ex);
    }
    if (st.blast_dmg) {                                    /* 每帧一个**新**源：一个源对同一敌人只结算一次（AUDIT U9）*/
        float center[3] = { s->ex, s->ey, pz };
        ce_damage_rect(center, 0.0f, 2, st.blast_dmg, FL_BLAST_W, FL_BLAST_H);
    }
    if (elapsed % 60 == 0 && blocked) ce_log("firelord: hp %d (blocked %u, frame %u)", s->hp, s->blocked, s->frames);
    if (st.died) {
        ce_anm_interrupt(s->anm_id, 1);                    /* 脚本 interruptLabel(1)：放大淡出后 delete */
        ce_anm_delete(s->ball_id);
        bar_destroy(s, 1);
        ce_play_sound(FL_SE_DEATH, s->x);
        ce_log("firelord: died after %u frames, %u moves, %u shots, %u blocked", s->frames, s->moves, s->shots, s->blocked);
        s->anm_id = 0; s->ball_id = 0; s->ball_active = 0; s->blast_left = 0;
        return 0;
    }
    return 1;
}

static void on_stage_start(ce_card_t *c) { dismiss(c, "stage start"); }
static void on_run_reset(ce_card_t *c)   { dismiss(c, "run reset"); }

CE_CARD(72, .active_recharge = FL_RECHARGE, .on_activate = on_activate, .on_active_tick = on_active_tick,
            .on_stage_start = on_stage_start, .on_run_reset = on_run_reset);
