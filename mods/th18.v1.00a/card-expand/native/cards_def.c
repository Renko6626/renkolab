/* cards_def.c —— 见 cards_def.h。纯 C11，无平台依赖。 */
#include <stdio.h>
#include <string.h>
#include "cards_def.h"

void ce_card_def_defaults(ce_card_def_t *d, uint32_t id)
{
    memset(d, 0, sizeof *d);
    d->id = id;
    snprintf(d->internal_name, sizeof d->internal_name, "%u", id);
    d->category     = 2;
    d->deck_visible = 1;
    d->hud_show     = 1;
    d->price_tier   = CE_CARD_UNSET;
    d->weight       = CE_CARD_UNSET;
    d->sprite_large = CE_CARD_UNSET;
    d->sprite_small = CE_CARD_UNSET;
}

int ce_card_text_ok(const char *s)
{
    if (!s || !s[0]) return 0;
    size_t n = strlen(s);
    if (n >= CE_CARD_TEXT_LINE) return 0;
    return strchr(s, '%') == NULL;
}

static int fail(char *err, unsigned cap, const char *field, const char *why)
{
    if (err && cap) snprintf(err, cap, "%s: %s", field, why);
    return 0;
}

static int in_range(char *err, unsigned cap, const char *field, uint32_t v, uint32_t lo, uint32_t hi, const char *why)
{
    if (v == CE_CARD_UNSET) return fail(err, cap, field, "required");
    if (v < lo || v > hi)   return fail(err, cap, field, why);
    return 1;
}

int ce_card_validate(const ce_card_def_t *d, char *err, unsigned cap)
{
    if (d->id < CE_CARD_ID_MIN || d->id > CE_CARD_ID_MAX)
        return fail(err, cap, "id", "must be 58..254 (56/57 are retail sentinels)");
    if (!ce_card_text_ok(d->name)) {
        if (err && cap) snprintf(err, cap, "name: \"%.40s\" — required, <= 63 bytes UTF-8, no '%%' (use U+FF05 fullwidth percent if you need one)", d->name);
        return 0;
    }
    if (d->ndesc > CE_CARD_DESC_LINES)
        return fail(err, cap, "desc", "at most 6 lines");
    for (unsigned i = 0; i < d->ndesc; ++i)
        if (!ce_card_text_ok(d->desc[i])) {
            if (err && cap) snprintf(err, cap, "desc[%u]: \"%.40s\" — each line <= 63 bytes UTF-8, non-empty, no '%%' (use U+FF05 fullwidth percent if you need one)", i, d->desc[i]);
            return 0;
        }
    if (!in_range(err, cap, "price_tier", d->price_tier, 0, 14, "must be 0..14 (price table 0x4b35c4)")) return 0;
    if (!in_range(err, cap, "weight", d->weight, 0, 255, "must be 0..255")) return 0;
    if (!in_range(err, cap, "dmode", d->dmode, 0, 12, "must be 0..12")) return 0;
    if (!in_range(err, cap, "repeatable", d->repeatable, 0, 1, "must be 0/1")) return 0;
    if (!in_range(err, cap, "deck_visible", d->deck_visible, 0, 1, "must be 0/1")) return 0;
    if (!in_range(err, cap, "initial_unlocked", d->initial_unlocked, 0, 1, "must be 0/1")) return 0;
    if (!in_range(err, cap, "hud_show", d->hud_show, 0, 1, "must be 0/1")) return 0;
    if (!in_range(err, cap, "category", d->category, 0, 3, "must be 0..3 (4 is the sentinel category)")) return 0;
    if (!in_range(err, cap, "f08", d->f08, 0, 1, "must be 0/1")) return 0;
    if (d->sprite_large == CE_CARD_UNSET) return fail(err, cap, "sprite_large", "required");
    if (d->sprite_small == CE_CARD_UNSET) return fail(err, cap, "sprite_small", "required");
    return 1;
}

static void put32(uint8_t *p, uint32_t v) { memcpy(p, &v, 4); }
static uint32_t get32(const uint8_t *p) { uint32_t v; memcpy(&v, p, 4); return v; }

void ce_card_encode_row(const ce_card_def_t *d, uint32_t name_ptr, uint8_t row[CE_ROW_BYTES])
{
    put32(row + 0x00, name_ptr);
    put32(row + 0x04, d->id);
    put32(row + 0x08, d->f08);
    put32(row + 0x0c, d->category);
    put32(row + 0x10, d->price_tier);
    put32(row + 0x14, d->weight);
    put32(row + 0x18, d->dmode);
    put32(row + 0x1c, d->repeatable);
    put32(row + 0x20, d->deck_visible);
    put32(row + 0x24, d->initial_unlocked);
    put32(row + 0x28, d->hud_show);
    put32(row + 0x2c, d->sprite_large);
    put32(row + 0x30, d->sprite_small);
}

int ce_shop_capacity_check(const uint8_t *table, unsigned nrows, unsigned *pool, unsigned *guaranteed,
                           char *err, unsigned cap)
{
    unsigned p = 0, g = CE_SHOP_RANDOM_MAX;
    for (unsigned r = 0; r < nrows; ++r) {
        const uint8_t *row = table + r * CE_ROW_BYTES;
        uint32_t id = get32(row + 0x04), w = get32(row + 0x14), dmode = get32(row + 0x18);
        if (id == 56 || id == 57) continue;                  /* 哨兵：装载器已把 +0x14 写成 6，且查表回落也到这里 */
        if (w == 0) ++g;
        else if (w != CE_SHOP_NEVER_WEIGHT) p += w + 5;      /* 从没拿过的卡再 +5 份（0x41712f），按最坏算 */
        if (dmode >= 1 && dmode <= 5) ++g;
    }
    if (pool) *pool = p;
    if (guaranteed) *guaranteed = g;
    if (p > CE_SHOP_POOL_SLOTS) {
        if (err && cap) snprintf(err, cap, "shop random pool %u slots > %u (sum of weight+5 over all cards)", p, (unsigned)CE_SHOP_POOL_SLOTS);
        return 0;
    }
    if (g > CE_SHOP_OFFER_SLOTS) {
        if (err && cap) snprintf(err, cap, "shop guaranteed offers %u > %u (weight==0 cards + stage cards + %u random)", g, (unsigned)CE_SHOP_OFFER_SLOTS, (unsigned)CE_SHOP_RANDOM_MAX);
        return 0;
    }
    return 1;
}


/* ── 开发用权重覆盖 ──────────────────────────────────────────────── */
unsigned ce_weight_override(uint8_t *table, unsigned nrows, int retail_weight, int new_weight,
                            const uint32_t *new_ids, unsigned n_new)
{
    unsigned changed = 0;
    if (retail_weight >= 0 && retail_weight <= 255) {
        for (unsigned id = 1; id < 56 && id < nrows; ++id) {           /* 0 空白卡、56/57 哨兵不动 */
            uint32_t *w = (uint32_t *)(table + id * CE_ROW_BYTES + 0x14);
            if (*w == 0 || *w == 6) continue;                           /* 保底资源卡 / 本来就不进池 */
            if (*w != (uint32_t)retail_weight) { *w = (uint32_t)retail_weight; ++changed; }
        }
    }
    if (new_weight >= 0 && new_weight <= 255) {
        for (unsigned i = 0; i < n_new; ++i) {
            if (new_ids[i] >= nrows) continue;
            uint32_t *w = (uint32_t *)(table + new_ids[i] * CE_ROW_BYTES + 0x14);
            if (*w == 0 || *w == 6) continue;
            if (*w != (uint32_t)new_weight) { *w = (uint32_t)new_weight; ++changed; }
        }
    }
    return changed;
}

unsigned ce_build_order(uint32_t *out, unsigned cap,
                        const uint32_t *retail, const uint32_t *retail_cat, unsigned nretail,
                        const uint32_t *new_ids, const uint32_t *new_cat, unsigned nnew,
                        uint32_t null_row, uint32_t back_row)
{
    unsigned n = 0;
    if (nretail + nnew + 1 > cap) return 0;
    for (unsigned i = 0; i < nretail; ++i) {
        out[n++] = retail[i];
        int last_of_cat = 1;                                   /* i 是不是该类别在零售表里的最后一张 */
        for (unsigned j = i + 1; j < nretail; ++j)
            if (retail_cat[j] == retail_cat[i]) { last_of_cat = 0; break; }
        if (!last_of_cat) continue;
        for (unsigned k = 0; k < nnew; ++k)
            if (new_cat[k] == retail_cat[i]) out[n++] = new_ids[k];
    }
    for (unsigned k = 0; k < nnew; ++k) {                      /* 类别在零售表里不存在的：排最后 */
        int seen = 0;
        for (unsigned i = 0; i < nretail; ++i) if (retail_cat[i] == new_cat[k]) { seen = 1; break; }
        if (!seen) out[n++] = new_ids[k];
    }
    unsigned visible = n;
    out[n++] = null_row;
    for (; n < cap; ++n) out[n] = back_row;
    return visible;
}
