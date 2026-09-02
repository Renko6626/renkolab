/* test_cards_def.c —— cards_def.c 的主机单测（Linux gcc 跑，不碰 Windows / thcrap）。
 *
 *   make test-host
 *
 * 只测纯逻辑：默认值、文案校验、字段范围、表行编码、商店容量。JSON 胶水（cards.c）只能在游戏里验。
 */
#include <stdio.h>
#include <string.h>
#include "../cards_def.h"

static int s_fail, s_pass;
#define CHECK(cond) do { if (cond) ++s_pass; else { ++s_fail; printf("  FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); } } while (0)

static uint32_t rd32(const uint8_t *p) { uint32_t v; memcpy(&v, p, 4); return v; }
static void wr32(uint8_t *p, uint32_t v) { memcpy(p, &v, 4); }

static void test_defaults(void)
{
    ce_card_def_t d;
    ce_card_def_defaults(&d, 58);
    CHECK(d.id == 58);
    CHECK(strcmp(d.internal_name, "58") == 0);
    CHECK(d.name[0] == 0 && d.ndesc == 0);
    CHECK(d.f08 == 0 && d.category == 2 && d.dmode == 0 && d.repeatable == 0);
    CHECK(d.deck_visible == 1 && d.initial_unlocked == 0 && d.hud_show == 1);
    CHECK(d.price_tier == CE_CARD_UNSET && d.weight == CE_CARD_UNSET);
    CHECK(d.sprite_large == CE_CARD_UNSET && d.sprite_small == CE_CARD_UNSET);
}

static void test_text_ok(void)
{
    char s64[65], s63[64];
    memset(s64, 'a', 64); s64[64] = 0;
    memset(s63, 'a', 63); s63[63] = 0;
    CHECK(ce_card_text_ok("测试卡牌"));
    CHECK(ce_card_text_ok(s63));
    CHECK(!ce_card_text_ok(s64));           /* 64 字节：放不进 0x40 连 NUL */
    CHECK(!ce_card_text_ok(""));
    CHECK(!ce_card_text_ok(NULL));
    CHECK(!ce_card_text_ok("100%"));        /* 会被当 printf 格式串 */
}

static ce_card_def_t good(void)
{
    ce_card_def_t d;
    ce_card_def_defaults(&d, 58);
    strcpy(d.name, "测试卡牌");
    strcpy(d.desc[0], "第一行"); strcpy(d.desc[1], "第二行"); d.ndesc = 2;
    d.price_tier = 5; d.weight = 2; d.sprite_large = 116; d.sprite_small = 117;
    return d;
}

static void test_validate(void)
{
    char err[128];
    ce_card_def_t d = good();
    CHECK(ce_card_validate(&d, err, sizeof err));

    d = good(); d.id = 57;  CHECK(!ce_card_validate(&d, err, sizeof err)); CHECK(strstr(err, "id") != NULL);
    d = good(); d.id = 255; CHECK(!ce_card_validate(&d, err, sizeof err));
    d = good(); d.id = 254; CHECK(ce_card_validate(&d, err, sizeof err));
    d = good(); d.name[0] = 0;              CHECK(!ce_card_validate(&d, err, sizeof err)); CHECK(strstr(err, "name") != NULL);
    d = good(); strcpy(d.name, "a%b");      CHECK(!ce_card_validate(&d, err, sizeof err));
    d = good(); strcpy(d.desc[1], "x%");    CHECK(!ce_card_validate(&d, err, sizeof err)); CHECK(strstr(err, "desc") != NULL);
    d = good(); d.ndesc = 7;                CHECK(!ce_card_validate(&d, err, sizeof err));
    d = good(); d.price_tier = CE_CARD_UNSET; CHECK(!ce_card_validate(&d, err, sizeof err)); CHECK(strstr(err, "price_tier") != NULL);
    d = good(); d.price_tier = 15;          CHECK(!ce_card_validate(&d, err, sizeof err));
    d = good(); d.price_tier = 14;          CHECK(ce_card_validate(&d, err, sizeof err));
    d = good(); d.weight = CE_CARD_UNSET;   CHECK(!ce_card_validate(&d, err, sizeof err)); CHECK(strstr(err, "weight") != NULL);
    d = good(); d.weight = 256;             CHECK(!ce_card_validate(&d, err, sizeof err));
    d = good(); d.weight = 0;               CHECK(ce_card_validate(&d, err, sizeof err));
    d = good(); d.dmode = 13;               CHECK(!ce_card_validate(&d, err, sizeof err)); CHECK(strstr(err, "dmode") != NULL);
    d = good(); d.repeatable = 2;           CHECK(!ce_card_validate(&d, err, sizeof err));
    d = good(); d.deck_visible = 2;         CHECK(!ce_card_validate(&d, err, sizeof err));
    d = good(); d.initial_unlocked = 2;     CHECK(!ce_card_validate(&d, err, sizeof err));
    d = good(); d.hud_show = 2;             CHECK(!ce_card_validate(&d, err, sizeof err));
    d = good(); d.category = 4;             CHECK(!ce_card_validate(&d, err, sizeof err)); CHECK(strstr(err, "category") != NULL);
    d = good(); d.f08 = 2;                  CHECK(!ce_card_validate(&d, err, sizeof err));
    d = good(); d.sprite_large = CE_CARD_UNSET; CHECK(!ce_card_validate(&d, err, sizeof err)); CHECK(strstr(err, "sprite_large") != NULL);
    d = good(); d.sprite_small = CE_CARD_UNSET; CHECK(!ce_card_validate(&d, err, sizeof err)); CHECK(strstr(err, "sprite_small") != NULL);
}

static void test_encode_row(void)
{
    ce_card_def_t d = good();
    d.f08 = 1; d.category = 3; d.dmode = 7; d.repeatable = 1; d.deck_visible = 0; d.initial_unlocked = 1; d.hud_show = 0;
    uint8_t row[CE_ROW_BYTES];
    memset(row, 0xee, sizeof row);
    ce_card_encode_row(&d, 0x12345678u, row);
    CHECK(rd32(row + 0x00) == 0x12345678u);   /* internal_name 指针 */
    CHECK(rd32(row + 0x04) == 58);            /* id */
    CHECK(rd32(row + 0x08) == 1);             /* f08 */
    CHECK(rd32(row + 0x0c) == 3);             /* category */
    CHECK(rd32(row + 0x10) == 5);             /* price_tier */
    CHECK(rd32(row + 0x14) == 2);             /* weight */
    CHECK(rd32(row + 0x18) == 7);             /* dmode */
    CHECK(rd32(row + 0x1c) == 1);             /* repeatable */
    CHECK(rd32(row + 0x20) == 0);             /* deck_visible */
    CHECK(rd32(row + 0x24) == 1);             /* initial_unlocked */
    CHECK(rd32(row + 0x28) == 0);             /* hud_show */
    CHECK(rd32(row + 0x2c) == 116);           /* sprite_large */
    CHECK(rd32(row + 0x30) == 117);           /* sprite_small */
}

/* 小表：行 = (id, weight, dmode) */
static void mkrow(uint8_t *t, unsigned r, uint32_t id, uint32_t weight, uint32_t dmode)
{
    uint8_t *p = t + r * CE_ROW_BYTES;
    memset(p, 0, CE_ROW_BYTES);
    wr32(p + 0x04, id); wr32(p + 0x14, weight); wr32(p + 0x18, dmode);
}

static void test_capacity(void)
{
    char err[160];
    uint8_t t[8 * CE_ROW_BYTES];
    unsigned pool, guaranteed;

    /* 普通：w2 → 7 份；w0 → 保证卡；dmode 3 → 本关必出；56/57 行忽略（哪怕 weight 0）；w6 不进池 */
    mkrow(t, 0, 0, 2, 0);
    mkrow(t, 1, 1, 0, 0);
    mkrow(t, 2, 2, 4, 3);
    mkrow(t, 3, 56, 0, 0);
    mkrow(t, 4, 57, 0, 0);
    mkrow(t, 5, 58, 6, 0);
    CHECK(ce_shop_capacity_check(t, 6, &pool, &guaranteed, err, sizeof err));
    CHECK(pool == 7 + 9);                     /* (2+5) + (4+5) */
    CHECK(guaranteed == 1 + 1 + CE_SHOP_RANDOM_MAX);   /* w0 一张 + dmode 1-5 一张 + 随机最多 6 */

    /* 池超限：80 张 weight 2 = 560 刚好过，81 张不过 */
    static uint8_t big[81 * CE_ROW_BYTES];
    for (unsigned i = 0; i < 81; ++i) mkrow(big, i, 58 + i, 2, 0);   /* 避开 56/57 */
    CHECK(ce_shop_capacity_check(big, 80, &pool, &guaranteed, err, sizeof err));
    CHECK(pool == 560);
    CHECK(!ce_shop_capacity_check(big, 81, &pool, &guaranteed, err, sizeof err));
    CHECK(strstr(err, "pool") != NULL);

    /* 保证卡超限：52 张 weight 0 → 52 + 6 = 58 > 57 */
    for (unsigned i = 0; i < 52; ++i) mkrow(big, i, 58 + i, 0, 0);
    CHECK(!ce_shop_capacity_check(big, 52, &pool, &guaranteed, err, sizeof err));
    CHECK(strstr(err, "guaranteed") != NULL);
    for (unsigned i = 0; i < 51; ++i) mkrow(big, i, 58 + i, 0, 0);
    CHECK(ce_shop_capacity_check(big, 51, &pool, &guaranteed, err, sizeof err));
}

int main(void)
{
    test_defaults();
    test_text_ok();
    test_validate();
    test_encode_row();
    test_capacity();
    printf("test_cards_def: %d passed, %d failed\n", s_pass, s_fail);
    return s_fail ? 1 : 0;
}
