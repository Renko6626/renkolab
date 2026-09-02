/* selfcheck.c —— 开机自检②：全有或全无的门。
 *
 * 起因是一种「日志一切正常」的静默失败：patch 里的 *_patch_init codecave
 * 是否被自动调用取决于 thcrap 版本；没被调用时新表全零、100 处 binhack
 * 指向一张空表，而 thcrap 日志里每条 binhack 都是 OK。
 *
 * 在 post_init（codecave 与 binhack 都已应用）做：
 *   1. 填表：零售 58 行 memcpy 进 codecave，多出的行填 NULL 副本。幂等。
 *   2. （战线 B）填跳转表：57 项原样拷，其余指向 case 56；核对两处分配器 binhack。
 *   3. 回读 100 处搬表站点：改后 4 字节 == cave + off，前缀 opcode 不变。
 *   4. 一行结论。
 */
#include <string.h>
#include "card_expand.h"

static int fill_table(uint8_t *base, uint8_t *cave)
{
    memcpy(cave, base + CE_TABLE_RVA, CE_ROW_COUNT * CE_ROW_SIZE);
    for (unsigned r = CE_ROW_COUNT; r < CE_ROWS; ++r)
        memcpy(cave + r * CE_ROW_SIZE, cave + CE_NULL_ROW * CE_ROW_SIZE, CE_ROW_SIZE);
    uint32_t id0  = *(uint32_t *)(cave + 4);
    uint32_t id56 = *(uint32_t *)(cave + CE_NULL_ROW * CE_ROW_SIZE + 4);
    if (id0 != 0 || id56 != CE_NULL_ROW) {
        ce_verdict("FAIL: table sanity after copy — row0.id=%u row56.id=%u", id0, id56);
        return 0;
    }
    ce_log("table: %u rows filled at %p (58 retail + %u NULL copies)",
           (unsigned)CE_ROWS, cave, (unsigned)(CE_ROWS - CE_ROW_COUNT));
    return 1;
}

#if CE_ALLOC
static int fill_jumptable(uint8_t *base)
{
    uint32_t *jt = (uint32_t *)ce_func_get(CE_JT_CAVE_NAME);
    if (!jt) { ce_verdict("FAIL: %s not found", CE_JT_CAVE_NAME); return 0; }
    const uint32_t *retail = (const uint32_t *)(base + CE_JT_RVA);
    memcpy(jt, retail, CE_JT_COUNT * 4);
    uint32_t case56 = (uint32_t)(uintptr_t)(base + CE_CASE56_RVA);
    for (unsigned i = CE_JT_COUNT; i < CE_ROWS; ++i) jt[i] = case56;
    /* 自证：项 56 就该是 case 56 的函数体；项 0 在模块内 */
    if (jt[CE_NULL_ROW] != case56 || jt[0] < (uint32_t)(uintptr_t)base) {
        ce_verdict("FAIL: jumptable sanity — [56]=%08x expected %08x", jt[CE_NULL_ROW], case56);
        return 0;
    }
    /* 两处分配器 binhack */
    const uint8_t *cmp = base + CE_ALLOC_CMP_RVA;       /* 83 fb <rows-1> */
    const uint8_t *jmp = base + CE_ALLOC_JMP_RVA;       /* ff 24 9d <jt> */
    uint32_t jt_addr = (uint32_t)(uintptr_t)jt;
    int ok_cmp = cmp[0] == 0x83 && cmp[1] == 0xfb && cmp[2] == (uint8_t)(CE_ROWS - 1);
    int ok_jmp = jmp[0] == 0xff && jmp[1] == 0x24 && jmp[2] == 0x9d && memcmp(jmp + 3, &jt_addr, 4) == 0;
    if (!ok_cmp || !ok_jmp) {
        ce_verdict("FAIL: allocator binhacks — bound %s (%02x %02x %02x), jumptable %s",
                   ok_cmp ? "ok" : "NOT patched", cmp[0], cmp[1], cmp[2],
                   ok_jmp ? "ok" : "NOT patched");
        return 0;
    }
    ce_log("jumptable: %u entries at %p (57 retail + %u -> case56 @ %08x); allocator bound = %u",
           (unsigned)CE_ROWS, jt, (unsigned)(CE_ROWS - CE_JT_COUNT), case56, (unsigned)(CE_ROWS - 1));
    return 1;
}
#endif

int ce_selfcheck_post_init(uint8_t *base)
{
    if (!ce_func_get) {
        ce_verdict("FAIL: func_get unavailable — cannot locate codecave; table NOT filled");
        return 0;
    }
    uint8_t *cave = (uint8_t *)ce_func_get(CE_CAVE_NAME);
    if (!cave) {
        ce_verdict("FAIL: %s not found — patch not in the stack?", CE_CAVE_NAME);
        return 0;
    }
    if (!fill_table(base, cave)) return 0;
#if CE_ALLOC
    if (!fill_jumptable(base)) return 0;
#endif

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
    if (bad == 0) {
        ce_verdict("OK: table filled (%u rows @ %p)%s, %u/%u sites verified",
                   (unsigned)CE_ROWS, cave, CE_ALLOC ? ", allocator relocated" : "",
                   ok, (unsigned)CE_NSITES);
        return 1;
    }
    const ce_site_t *s = &CE_SITES[first_bad];
    const uint8_t *p = base + s->rva;
    ce_verdict("FAIL: %u/%u sites verified, %u NOT patched. first bad @ 0x%08x: "
               "%02x %02x %02x %02x %02x %02x %02x — partial application, DO NOT PLAY",
               ok, (unsigned)CE_NSITES, bad, 0x400000u + s->rva,
               p[0], p[1], p[2], p[3], p[4], p[5], p[6]);
    return 0;
}
