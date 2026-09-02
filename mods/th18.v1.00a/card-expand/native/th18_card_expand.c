/* th18_card_expand.dll —— 卡表搬迁的「全有或全无的门」。
 *
 * 只有一个真正的入口：th18_card_expand_mod_post_init。
 * thcrap 在 runconfig_stage_apply 之后调它（init.cpp:407 → :420），
 * 也就是**所有 codecave 和 binhack 都已应用完**的时刻。它做三件事：
 *
 *   1. 填表：把零售 58 行从游戏自己的 .data 拷进 codecave，多出的行填成
 *      NULL 行副本。幂等——patch 里那个 *_patch_init codecave 跑没跑都对。
 *   2. 回读验证：100 处 binhack 逐一比对「前缀 + (cave + 偏移)」。
 *   3. 写日志：进 thcrap 自己的日志；拿不到 log_printf 就退到文件。
 *
 * 为什么不靠 *_patch_init：它在 codecaves_apply 末尾跑，早于 binhacks_apply，
 * 验不了 binhack；更要紧的是，它是否被调用取决于 thcrap 版本，而失败时
 * **日志一切正常** —— 新表全零、100 处指向空表。这个 DLL 把两种静默失败
 * 都变成日志里的一行红字。
 *
 * 不链接 thcrap.dll 的导入库：func_get / log_printf 都用 GetProcAddress 取，
 * 拿不到就降级，不崩。
 */
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include "sites_gen.h"

typedef uintptr_t (*func_get_t)(const char *);
typedef void      (*log_printf_t)(const char *, ...);

static log_printf_t s_log_printf;
static func_get_t   s_func_get;

static void lg(const char *fmt, ...)
{
    char buf[512];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof buf, fmt, ap);
    va_end(ap);
    if (s_log_printf) {
        s_log_printf("[th18_card_expand] %s\n", buf);
        return;
    }
    FILE *f = fopen("th18_card_expand.log", "a");
    if (f) { fprintf(f, "%s\n", buf); fclose(f); }
}

int __stdcall thcrap_plugin_init(void)
{
    HMODULE th = GetModuleHandleA("thcrap.dll");
    if (th) {
        s_log_printf = (log_printf_t)GetProcAddress(th, "log_printf");
        s_func_get   = (func_get_t)  GetProcAddress(th, "func_get");
    }
    lg("plugin loaded; log_printf=%s func_get=%s",
       s_log_printf ? "ok" : "MISSING", s_func_get ? "ok" : "MISSING");
    return 0;                      /* 0 = 留驻 */
}

/* 名字里的 _mod_ 之后是 post_init → mod_func_run_all("post_init") 会调它。
 * 签名按 mod_call_type = void (TH_CDECL*)(void*)（plugin.h:71）。*/
void __cdecl th18_card_expand_mod_post_init(void *param)
{
    (void)param;
    if (!s_func_get) {
        lg("FAIL: func_get unavailable — cannot locate codecave; table NOT filled");
        return;
    }
    uint8_t *cave = (uint8_t *)s_func_get(CE_CAVE_NAME);
    if (!cave) {
        lg("FAIL: %s not found — patch not loaded?", CE_CAVE_NAME);
        return;
    }
    uint8_t *base = (uint8_t *)GetModuleHandleA(NULL);
    const uint8_t *retail = base + CE_TABLE_RVA;

    /* 1. 填表（幂等） */
    memcpy(cave, retail, CE_ROW_COUNT * CE_ROW_SIZE);
    for (unsigned r = CE_ROW_COUNT; r < CE_ROWS; ++r)
        memcpy(cave + r * CE_ROW_SIZE, cave + CE_NULL_ROW * CE_ROW_SIZE, CE_ROW_SIZE);

    /* 表填对了的最小自证：行 0 的 id 字段 == 0、行 56 的 id == 56 */
    uint32_t id0  = *(uint32_t *)(cave + 4);
    uint32_t id56 = *(uint32_t *)(cave + CE_NULL_ROW * CE_ROW_SIZE + 4);
    if (id0 != 0 || id56 != CE_NULL_ROW) {
        lg("FAIL: table sanity — row0.id=%u row56.id=%u (expected 0 / %u)", id0, id56, CE_NULL_ROW);
        return;
    }

    /* 2. 回读验证 100 处 */
    unsigned ok = 0, bad = 0, first_bad = 0;
    for (unsigned i = 0; i < CE_NSITES; ++i) {
        const ce_site_t *s = &CE_SITES[i];
        const uint8_t *p = base + s->rva;
        uint32_t want = (uint32_t)(uintptr_t)cave + s->off;
        int match = memcmp(p, s->prefix, s->prefix_len) == 0
                 && memcmp(p + s->prefix_len, &want, 4) == 0
                 && s->prefix_len + 4 == s->len;
        if (match) { ++ok; }
        else { if (!bad) first_bad = i; ++bad; }
    }

    /* 3. 结论 */
    if (bad == 0) {
        lg("OK: table filled (%u rows @ %p), %u/%u sites verified",
           (unsigned)CE_ROWS, cave, ok, (unsigned)CE_NSITES);
    } else {
        const ce_site_t *s = &CE_SITES[first_bad];
        const uint8_t *p = base + s->rva;
        lg("FAIL: %u/%u sites verified, %u NOT patched. first bad @ 0x%08x: "
           "%02x %02x %02x %02x %02x %02x %02x — partial application, DO NOT PLAY",
           ok, (unsigned)CE_NSITES, bad, 0x400000u + s->rva,
           p[0], p[1], p[2], p[3], p[4], p[5], p[6]);
    }
}
