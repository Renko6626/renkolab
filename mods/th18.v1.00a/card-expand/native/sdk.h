/* sdk.h —— 写一张行为卡时 include 这个。用法与机制见 ../SDK.md。
 *
 *   #include "sdk.h"
 *   static int on_death_frame2(ce_card_t *c) { ... return 0; }
 *   CE_CARD(62, .on_death_frame2 = on_death_frame2);
 *
 * CE_CARD 展开：这张卡的回调表 → 21 个 __thiscall 桩 → 一份 21 槽虚表 → 登记进 ce_behaviors。
 * 桩按虚表分派（每张卡一套桩），没写的回调桩返回 0（= 基类槽 `xor eax,eax; ret` 的效果）。
 * +0x08 / +0x38 / +0x3c / +0x40（主动卡 C 键与充能三件套）本批不覆盖，直接指基类实现。
 * +0x50 operator_delete：先释放私有状态，再进基类的 delete。
 */
#pragma once
#include <stdint.h>
#include "engine.h"
#include "sdk_core.h"

typedef struct ce_card ce_card_t;          /* = zCardBaseClass*，只通过下面的取值函数看 */

#define ce_card_id(c)     (*(uint32_t *)((uint8_t *)(c) + CE_CARD_ID))
#define ce_card_entry(c)  (*(uint8_t **)((uint8_t *)(c) + CE_CARD_TABLE_ENTRY))
#define ce_card_flags(c)  (*(uint32_t *)((uint8_t *)(c) + CE_CARD_FLAGS))
#define ce_state(c, T)    ((T *)ce_state_alloc((c), sizeof(T)))     /* 私有状态（SDK §4）*/

typedef struct {
    int  (*ctor)(ce_card_t *);                                   /* +0x00 非 0 = 当场删卡 */
    int  (*dtor)(ce_card_t *);                                   /* +0x04 */
    int  (*on_death_after_deathbomb)(ce_card_t *, uint32_t);     /* +0x0c 非 0 = 救下了 */
    int  (*on_death_before_deathbomb)(ce_card_t *);              /* +0x10 */
    int  (*on_death_frame2)(ce_card_t *);                        /* +0x14 结算之后 */
    int  (*on_power_level_change)(ce_card_t *);                  /* +0x18 */
    int  (*on_tick_shooters)(ce_card_t *, uint32_t, uint32_t);   /* +0x1c */
    int  (*on_load)(ce_card_t *);                                /* +0x20 */
    int  (*on_tick)(ce_card_t *);                                /* +0x24 Player tick 内（在移速倍率复位之前，别在这写移速）*/
    int  (*on_bullet_created)(ce_card_t *, void *bullet);        /* +0x28 */
    int  (*on_tick_2)(ce_card_t *);                              /* +0x2c AbilityManager tick，先于 Player tick；菜单里不跑 */
    int  (*on_enemy_drop)(ce_card_t *, uint32_t, uint32_t);      /* +0x30 */
    void (*on_stage_start)(ce_card_t *);                         /* +0x34 */
    int  (*on_hud_anm)(ce_card_t *, uint32_t);                   /* +0x44 */
    int  (*on_draw)(ce_card_t *);                                /* +0x48 */
    void (*on_run_reset)(ce_card_t *);                           /* +0x4c */
    /* 虚表之外的事件（SDK §6，断点实现）*/
    void (*on_item_score)(ce_card_t *, int32_t *value);          /* 道具身价算完、显示与计分之前 */
} ce_hooks_t;

/* sdk.c */
void ce_sdk_trace(uint32_t id, unsigned slot, const char *name);   /* trace 开着才记；每张卡每槽记第一次 */
void ce_sdk_register_or_log(const ce_behavior_t *b);

#define CE_TC __attribute__((thiscall))
typedef int  (CE_TC *ce_base_fn0_t)(void *);
typedef void (CE_TC *ce_base_del_t)(void *, uint32_t);

/* ---- 桩生成 ---- */
#define CE_STUB0(ID, NAME, SLOT) \
    static int CE_TC ce_s_##ID##_##NAME(void *self) { \
        ce_sdk_trace(ID, SLOT, #NAME); \
        return ce_hooks_##ID.NAME ? ce_hooks_##ID.NAME((ce_card_t *)self) : 0; }
#define CE_STUB1(ID, NAME, SLOT, T1) \
    static int CE_TC ce_s_##ID##_##NAME(void *self, T1 a) { \
        ce_sdk_trace(ID, SLOT, #NAME); \
        return ce_hooks_##ID.NAME ? ce_hooks_##ID.NAME((ce_card_t *)self, a) : 0; }
#define CE_STUB2(ID, NAME, SLOT) \
    static int CE_TC ce_s_##ID##_##NAME(void *self, uint32_t a, uint32_t b) { \
        ce_sdk_trace(ID, SLOT, #NAME); \
        return ce_hooks_##ID.NAME ? ce_hooks_##ID.NAME((ce_card_t *)self, a, b) : 0; }
#define CE_STUBV(ID, NAME, SLOT) \
    static void CE_TC ce_s_##ID##_##NAME(void *self) { \
        ce_sdk_trace(ID, SLOT, #NAME); \
        if (ce_hooks_##ID.NAME) ce_hooks_##ID.NAME((ce_card_t *)self); }

#define CE_CARD(ID, ...) \
    static const ce_hooks_t ce_hooks_##ID = { __VA_ARGS__ }; \
    CE_STUB0(ID, ctor, 0x00) \
    CE_STUB0(ID, dtor, 0x04) \
    CE_STUB1(ID, on_death_after_deathbomb, 0x0c, uint32_t) \
    CE_STUB0(ID, on_death_before_deathbomb, 0x10) \
    CE_STUB0(ID, on_death_frame2, 0x14) \
    CE_STUB0(ID, on_power_level_change, 0x18) \
    CE_STUB2(ID, on_tick_shooters, 0x1c) \
    CE_STUB0(ID, on_load, 0x20) \
    CE_STUB0(ID, on_tick, 0x24) \
    CE_STUB1(ID, on_bullet_created, 0x28, void *) \
    CE_STUB0(ID, on_tick_2, 0x2c) \
    CE_STUB2(ID, on_enemy_drop, 0x30) \
    CE_STUBV(ID, on_stage_start, 0x34) \
    CE_STUB1(ID, on_hud_anm, 0x44, uint32_t) \
    CE_STUB0(ID, on_draw, 0x48) \
    CE_STUBV(ID, on_run_reset, 0x4c) \
    static void CE_TC ce_s_##ID##_opdelete(void *self, uint32_t flag) { \
        ce_sdk_trace(ID, 0x50, "operator_delete"); \
        ce_state_free(self); \
        ((ce_base_del_t)CE_BASE_SLOT_OPDELETE)(self, flag); } \
    static const void *const ce_vt_##ID[21] = { \
        (const void *)ce_s_##ID##_ctor,                      /* +0x00 */ \
        (const void *)ce_s_##ID##_dtor,                      /* +0x04 */ \
        (const void *)CE_BASE_SLOT_C_PRESS,                  /* +0x08 主动卡，本批不覆盖 */ \
        (const void *)ce_s_##ID##_on_death_after_deathbomb,  /* +0x0c */ \
        (const void *)ce_s_##ID##_on_death_before_deathbomb, /* +0x10 */ \
        (const void *)ce_s_##ID##_on_death_frame2,           /* +0x14 */ \
        (const void *)ce_s_##ID##_on_power_level_change,     /* +0x18 */ \
        (const void *)ce_s_##ID##_on_tick_shooters,          /* +0x1c */ \
        (const void *)ce_s_##ID##_on_load,                   /* +0x20 */ \
        (const void *)ce_s_##ID##_on_tick,                   /* +0x24 */ \
        (const void *)ce_s_##ID##_on_bullet_created,         /* +0x28 */ \
        (const void *)ce_s_##ID##_on_tick_2,                 /* +0x2c */ \
        (const void *)ce_s_##ID##_on_enemy_drop,             /* +0x30 */ \
        (const void *)ce_s_##ID##_on_stage_start,            /* +0x34 */ \
        (const void *)CE_BASE_SLOT_METHOD_38,                /* +0x38 充能 */ \
        (const void *)CE_BASE_SLOT_METHOD_3C,                /* +0x3c */ \
        (const void *)CE_BASE_SLOT_METHOD_40,                /* +0x40 */ \
        (const void *)ce_s_##ID##_on_hud_anm,                /* +0x44 */ \
        (const void *)ce_s_##ID##_on_draw,                   /* +0x48 */ \
        (const void *)ce_s_##ID##_on_run_reset,              /* +0x4c */ \
        (const void *)ce_s_##ID##_opdelete,                  /* +0x50 */ \
    }; \
    static const ce_behavior_t ce_beh_##ID = { ID, ce_vt_##ID, #__VA_ARGS__, &ce_hooks_##ID }; \
    __attribute__((constructor)) static void ce_reg_##ID(void) { ce_sdk_register_or_log(&ce_beh_##ID); }
