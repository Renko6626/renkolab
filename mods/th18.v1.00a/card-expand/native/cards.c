/* cards.c —— 战线 E 第 10 段：从 thcrap 栈里的 th18/cards.js 装新卡。
 *
 * 门里（BP_ce_gate，填表之后、菜单 setup 之前）调一次 ce_cards_load：
 *   1. stack_game_json_resolve("cards.js")：thcrap 把栈里每个 patch 的 th18/cards.js 深合并成一个对象。
 *      NULL = 栈里没有这个文件 = 0 张新卡，不是错。
 *   2. 顶层每个键 = id 的十进制（58..254），值 = 对象；字段见 ../DATA.md §2。
 *      逐张：默认值 → 取字段 → ce_card_validate → 查重 → 写 cave 第 id 行 → ce_text_set → 登记。
 *   3. cave 里 56（NULL）/ 57（BACK）两行 +0x14 := 6：商店三处循环的上界已抬到 rows，幻影 id 查表回落到
 *      NULL 行，BACK 按自己的 id 命中，两行权重 6 让三条筛选（≠0&&≠6 / ==0 / dmode 1-5）都过不了。AUDIT §N1。
 *   4. ce_shop_capacity_check：随机池 ≤ 560 份、保证卡 ≤ 57（AUDIT §N2、边界 #34）。
 * 任何一条错 → FAIL verdict、返回 0，selfcheck 还原分配器上界——全有或全无。
 *
 * thcrap / jansson 的函数全部 GetProcAddress（不链接导入库，同 func_get）。json_t 只用到 ->type：
 * jansson 2.x 的 `struct json_t { json_type type; volatile size_t refcount; }` 与枚举顺序
 * OBJECT ARRAY STRING INTEGER REAL TRUE FALSE NULL 自 2.0 起没变过；根对象的 type 必须是 OBJECT，
 * 否则当作布局假设失效 FAIL（而不是把别的字段读成类型）。
 *
 * internal_name（表行 +0x00）指向 DLL 里 strdup 出来的串，DLL 与游戏同生命周期，不释放。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "card_expand.h"

/* ---- jansson 最小映射 ---- */
typedef struct json_t { int type; size_t refcount; } json_t;
enum { J_OBJECT = 0, J_ARRAY, J_STRING, J_INTEGER, J_REAL, J_TRUE, J_FALSE, J_NULL };

static json_t     *(*p_stack_game_json_resolve)(const char *, size_t *);
static json_t     *(*p_json_decref_safe)(json_t *);
static void       *(*p_json_object_iter)(json_t *);
static const char *(*p_json_object_iter_key)(void *);
static json_t     *(*p_json_object_iter_value)(void *);
static void       *(*p_json_object_iter_next)(json_t *, void *);
static json_t     *(*p_json_object_get)(const json_t *, const char *);
static long long   (*p_json_integer_value)(const json_t *);
static const char *(*p_json_string_value)(const json_t *);
static size_t      (*p_json_array_size)(const json_t *);
static json_t     *(*p_json_array_get)(const json_t *, size_t);

static int resolve_api(void)
{
    struct { const char *dll; const char *name; void **slot; } tab[] = {
        { "thcrap.dll",  "stack_game_json_resolve", (void **)&p_stack_game_json_resolve },
        { "thcrap.dll",  "json_decref_safe",        (void **)&p_json_decref_safe },
        { "jansson.dll", "json_object_iter",        (void **)&p_json_object_iter },
        { "jansson.dll", "json_object_iter_key",    (void **)&p_json_object_iter_key },
        { "jansson.dll", "json_object_iter_value",  (void **)&p_json_object_iter_value },
        { "jansson.dll", "json_object_iter_next",   (void **)&p_json_object_iter_next },
        { "jansson.dll", "json_object_get",         (void **)&p_json_object_get },
        { "jansson.dll", "json_integer_value",      (void **)&p_json_integer_value },
        { "jansson.dll", "json_string_value",       (void **)&p_json_string_value },
        { "jansson.dll", "json_array_size",         (void **)&p_json_array_size },
        { "jansson.dll", "json_array_get",          (void **)&p_json_array_get },
    };
    for (unsigned i = 0; i < sizeof tab / sizeof tab[0]; ++i) {
        HMODULE m = GetModuleHandleA(tab[i].dll);
        void *f = m ? (void *)GetProcAddress(m, tab[i].name) : NULL;
        if (!f) { ce_verdict("FAIL: cards: %s missing from %s — cannot read cards.js", tab[i].name, tab[i].dll); return 0; }
        *tab[i].slot = f;
    }
    return 1;
}

/* ---- 注册表 ---- */
static uint32_t s_ids[CE_CARD_MAX_NEW];
static uint8_t  s_initial_unlocked[CE_CARD_MAX_NEW];
static unsigned s_count;

unsigned ce_new_card_count(void)               { return s_count; }
uint32_t ce_new_card_id(unsigned i)            { return i < s_count ? s_ids[i] : 0; }
int      ce_new_card_initial_unlocked(unsigned i) { return i < s_count && s_initial_unlocked[i]; }

/* ---- 取字段 ---- */
static const char *const KNOWN[] = {
    "name", "desc", "internal_name", "price_tier", "weight", "dmode", "repeatable",
    "deck_visible", "initial_unlocked", "hud_show", "category", "f08", "sprite_large", "sprite_small", NULL
};

/* 整数字段：缺省 → 不动 out；类型不是整数或负 → 0 并填 err */
static int get_uint(const json_t *obj, const char *key, uint32_t *out, char *err, unsigned cap)
{
    const json_t *v = p_json_object_get(obj, key);
    if (!v) return 1;
    if (v->type != J_INTEGER) { snprintf(err, cap, "%s: must be a JSON integer (not a string/float)", key); return 0; }
    long long n = p_json_integer_value(v);
    if (n < 0 || n > 0xffffffffLL) { snprintf(err, cap, "%s: out of range", key); return 0; }
    *out = (uint32_t)n;
    return 1;
}

/* 字串字段：缺省 → 不动 out；类型不对 → 0 */
static int get_str(const json_t *obj, const char *key, char *out, unsigned cap_out, char *err, unsigned cap)
{
    const json_t *v = p_json_object_get(obj, key);
    if (!v) return 1;
    if (v->type != J_STRING) { snprintf(err, cap, "%s: must be a JSON string", key); return 0; }
    const char *s = p_json_string_value(v);
    if (!s || strlen(s) >= cap_out) { snprintf(err, cap, "%s: too long (max %u bytes)", key, cap_out - 1); return 0; }
    strcpy(out, s);
    return 1;
}

static int parse_key(const char *key, uint32_t *id)
{
    if (!key[0] || strlen(key) > 3) return 0;
    for (const char *p = key; *p; ++p) if (*p < '0' || *p > '9') return 0;
    if (key[0] == '0' && key[1]) return 0;                 /* 无前导零 */
    *id = (uint32_t)strtoul(key, NULL, 10);
    return 1;
}

static int parse_card(const char *key, const json_t *obj, ce_card_def_t *d, char *err, unsigned cap)
{
    uint32_t id;
    if (!parse_key(key, &id)) { snprintf(err, cap, "key \"%s\": must be the card id in decimal (58..254)", key); return 0; }
    ce_card_def_defaults(d, id);
    if (obj->type != J_OBJECT) { snprintf(err, cap, "value must be an object"); return 0; }

    for (void *it = p_json_object_iter((json_t *)obj); it; it = p_json_object_iter_next((json_t *)obj, it)) {
        const char *k = p_json_object_iter_key(it);
        unsigned known = 0;
        for (unsigned i = 0; KNOWN[i]; ++i) if (strcmp(k, KNOWN[i]) == 0) { known = 1; break; }
        if (!known) ce_log("cards: %s: unknown field \"%s\" ignored", key, k);
    }
    if (!get_str(obj, "name", d->name, sizeof d->name, err, cap)) return 0;
    if (!get_str(obj, "internal_name", d->internal_name, sizeof d->internal_name, err, cap)) return 0;
    const json_t *desc = p_json_object_get(obj, "desc");
    if (desc) {
        if (desc->type != J_ARRAY) { snprintf(err, cap, "desc: must be an array of strings"); return 0; }
        size_t n = p_json_array_size(desc);
        if (n > CE_CARD_DESC_LINES) { snprintf(err, cap, "desc: at most %u lines", (unsigned)CE_CARD_DESC_LINES); return 0; }
        for (size_t i = 0; i < n; ++i) {
            const json_t *line = p_json_array_get(desc, i);
            const char *s = line && line->type == J_STRING ? p_json_string_value(line) : NULL;
            if (!s) { snprintf(err, cap, "desc[%u]: must be a string", (unsigned)i); return 0; }
            if (strlen(s) >= CE_CARD_TEXT_LINE) { snprintf(err, cap, "desc[%u]: too long (max 63 bytes)", (unsigned)i); return 0; }
            strcpy(d->desc[i], s);
        }
        d->ndesc = (unsigned)n;
    }
    struct { const char *k; uint32_t *p; } ints[] = {
        { "price_tier", &d->price_tier }, { "weight", &d->weight }, { "dmode", &d->dmode },
        { "repeatable", &d->repeatable }, { "deck_visible", &d->deck_visible },
        { "initial_unlocked", &d->initial_unlocked }, { "hud_show", &d->hud_show },
        { "category", &d->category }, { "f08", &d->f08 },
        { "sprite_large", &d->sprite_large }, { "sprite_small", &d->sprite_small },
    };
    for (unsigned i = 0; i < sizeof ints / sizeof ints[0]; ++i)
        if (!get_uint(obj, ints[i].k, ints[i].p, err, cap)) return 0;
    return ce_card_validate(d, err, cap);
}

/* ---- 入口 ---- */
static void exclude_sentinels(uint8_t *cave)
{
    uint32_t six = CE_SHOP_NEVER_WEIGHT;
    memcpy(cave + CE_NULL_ROW * CE_ROW_BYTES + 0x14, &six, 4);          /* 56 NULL：幻影 id 的回落行 */
    memcpy(cave + (CE_NULL_ROW + 1) * CE_ROW_BYTES + 0x14, &six, 4);    /* 57 BACK */
}

int ce_cards_load(uint8_t *base, uint8_t *cave, unsigned rows)
{
    (void)base;
    char err[160];
    s_count = 0;
    if (!resolve_api()) return 0;

    json_t *root = p_stack_game_json_resolve("cards.js", NULL);
    if (!root) {
        exclude_sentinels(cave);
        ce_log("cards: no th18/cards.js in the patch stack — 0 new cards (NULL/BACK weight := 6 for the shop)");
        return 1;
    }
    if (root->type != J_OBJECT) {
        ce_verdict("FAIL: cards: cards.js root is not an object (type %d) — or jansson layout differs", root->type);
        p_json_decref_safe(root);
        return 0;
    }

    uint8_t seen[CE_MAX_ROWS] = { 0 };
    int ok = 1;
    for (void *it = p_json_object_iter(root); it && ok; it = p_json_object_iter_next(root, it)) {
        const char *key = p_json_object_iter_key(it);
        json_t *val = p_json_object_iter_value(it);
        ce_card_def_t d;
        if (!parse_card(key, val, &d, err, sizeof err)) {
            ce_verdict("FAIL: cards: card \"%s\": %s", key, err); ok = 0; break;
        }
        if (d.id >= rows) { ce_verdict("FAIL: cards: card %u: id >= table rows (%u)", d.id, rows); ok = 0; break; }
        if (seen[d.id])   { ce_verdict("FAIL: cards: card %u: duplicate id", d.id); ok = 0; break; }
        if (s_count >= CE_CARD_MAX_NEW) {
            ce_verdict("FAIL: cards: more than %u new cards (encyclopedia count 56+N must fit cmp r,imm8)", (unsigned)CE_CARD_MAX_NEW);
            ok = 0; break;
        }
        seen[d.id] = 1;
        char *name = _strdup(d.internal_name);
        ce_card_encode_row(&d, (uint32_t)(uintptr_t)name, cave + d.id * CE_ROW_BYTES);
        ce_text_set(d.id, d.name, (const char (*)[CE_CARD_TEXT_LINE])d.desc, d.ndesc);
        s_ids[s_count] = d.id;
        s_initial_unlocked[s_count] = (uint8_t)d.initial_unlocked;
        ++s_count;
        ce_log("cards: %u \"%s\" (%s) tier %u weight %u dmode %u sprites %u/%u%s",
               d.id, d.name, d.internal_name, d.price_tier, d.weight, d.dmode, d.sprite_large, d.sprite_small,
               d.initial_unlocked ? " initial_unlocked" : "");
    }
    p_json_decref_safe(root);
    if (!ok) { s_count = 0; return 0; }

    exclude_sentinels(cave);
    unsigned pool = 0, guaranteed = 0;
    if (!ce_shop_capacity_check(cave, rows, &pool, &guaranteed, err, sizeof err)) {
        ce_verdict("FAIL: cards: %s", err); s_count = 0; return 0;
    }
    ce_log("cards: %u registered from cards.js; shop pool %u/%u slots, guaranteed offers <= %u/%u",
           s_count, pool, (unsigned)CE_SHOP_POOL_SLOTS, guaranteed, (unsigned)CE_SHOP_OFFER_SLOTS);
    return 1;
}
