/* selfcheck.c —— 开机自检②：全有或全无的门。
 *
 * 起因是一种「日志一切正常」的静默失败：patch 里的 *_patch_init codecave
 * 是否被自动调用取决于 thcrap 版本；没被调用时新表全零、100 处 binhack
 * 指向一张空表，而 thcrap 日志里每条 binhack 都是 OK。
 *
 * 这里在 post_init（codecave 与 binhack 都已应用）做三件事：
 *   1. 填表：零售 58 行 memcpy 进 codecave，多出的行填 NULL 副本。幂等。
 *   2. 回读 100 处：改后 4 字节应等于 cave + off，前缀 opcode 不变。
 *   3. 一行结论进日志。
 */
#include <string.h>
#include "card_expand.h"

int ce_selfcheck_post_init(uint8_t *base)
{
    if (!ce_func_get) {
        ce_log("FAIL: func_get unavailable — cannot locate codecave; table NOT filled");
        return 0;
    }
    uint8_t *cave = (uint8_t *)ce_func_get(CE_CAVE_NAME);
    if (!cave) {
        ce_log("FAIL: %s not found — patch not in the stack?", CE_CAVE_NAME);
        return 0;
    }
    const uint8_t *retail = base + CE_TABLE_RVA;

    /* 1. 填表（幂等） */
    memcpy(cave, retail, CE_ROW_COUNT * CE_ROW_SIZE);
    for (unsigned r = CE_ROW_COUNT; r < CE_ROWS; ++r)
        memcpy(cave + r * CE_ROW_SIZE, cave + CE_NULL_ROW * CE_ROW_SIZE, CE_ROW_SIZE);

    uint32_t id0  = *(uint32_t *)(cave + 4);
    uint32_t id56 = *(uint32_t *)(cave + CE_NULL_ROW * CE_ROW_SIZE + 4);
    if (id0 != 0 || id56 != CE_NULL_ROW) {
        ce_log("FAIL: table sanity after copy — row0.id=%u row56.id=%u", id0, id56);
        return 0;
    }

    /* 2. 回读 100 处 */
    unsigned ok = 0, bad = 0, first_bad = 0;
    for (unsigned i = 0; i < CE_NSITES; ++i) {
        const ce_site_t *s = &CE_SITES[i];
        const uint8_t *p = base + s->rva;
        uint32_t want = (uint32_t)(uintptr_t)cave + s->off;
        int match = s->prefix_len + 4 == s->len
                 && memcmp(p, s->prefix, s->prefix_len) == 0
                 && memcmp(p + s->prefix_len, &want, 4) == 0;
        if (match) ++ok; else { if (!bad) first_bad = i; ++bad; }
    }

    /* 3. 结论 */
    if (bad == 0) {
        ce_log("OK: table filled (%u rows @ %p), %u/%u sites verified",
               (unsigned)CE_ROWS, cave, ok, (unsigned)CE_NSITES);
        return 1;
    }
    const ce_site_t *s = &CE_SITES[first_bad];
    const uint8_t *p = base + s->rva;
    ce_log("FAIL: %u/%u sites verified, %u NOT patched. first bad @ 0x%08x: "
           "%02x %02x %02x %02x %02x %02x %02x — partial application, DO NOT PLAY",
           ok, (unsigned)CE_NSITES, bad, 0x400000u + s->rva,
           p[0], p[1], p[2], p[3], p[4], p[5], p[6]);
    return 0;
}
