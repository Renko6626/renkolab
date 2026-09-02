/* dll_main.c —— th18_card_expand.dll 的入口、日志与开机自检①。
 *
 * thcrap 的两个回调：
 *   thcrap_plugin_init              插件加载时（早于 patch 应用）。自检①：
 *                                   零售表还在预期的地方、长预期的样子。
 *   th18_card_expand_mod_post_init  runconfig_stage_apply 之后（init.cpp:407→:420），
 *                                   codecave 与 binhack 都已应用。自检②（selfcheck.c）。
 *
 * 不链接 thcrap.dll 的导入库：func_get / log_printf 都用 GetProcAddress 取，
 * 拿不到就降级，不崩。
 */
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <time.h>
#include "card_expand.h"

static void (*s_log_printf)(const char *, ...);
uintptr_t (*ce_func_get)(const char *);
static char s_logpath[MAX_PATH];

static FILE *open_log(const char *mode)
{
    FILE *f = fopen(s_logpath, mode);
    if (!f) {
        char tmp[MAX_PATH];
        if (GetTempPathA(sizeof tmp, tmp)) {
            strncat(tmp, "th18_card_expand.log", sizeof tmp - strlen(tmp) - 1);
            f = fopen(tmp, mode);
            if (f) strncpy(s_logpath, tmp, sizeof s_logpath - 1);
        }
    }
    return f;
}

static void vlog(const char *fmt, va_list ap)
{
    FILE *f = open_log("a");
    if (!f) return;
    vfprintf(f, fmt, ap);
    fputc('\n', f);
    fclose(f);
}

void ce_log(const char *fmt, ...)
{
    va_list ap; va_start(ap, fmt); vlog(fmt, ap); va_end(ap);
}

void ce_verdict(const char *fmt, ...)
{
    char buf[512];
    va_list ap; va_start(ap, fmt); vsnprintf(buf, sizeof buf, fmt, ap); va_end(ap);
    ce_log("%s", buf);
    if (s_log_printf) s_log_printf("[th18_card_expand] %s\n", buf);
}

/* 自检①：零售表签名。三个字段就够把「这不是 th18 v1.00a」拦下来：
 *   行 0  id == 0
 *   行 56 id == 56 且 internal_name 指向 "NULL"
 * 不 md5 整个 exe——那要读文件，而这三个字段就是我们要搬的东西本身。*/
static int retail_table_looks_right(const uint8_t *base)
{
    const uint8_t *t = base + CE_TABLE_RVA;
    uint32_t id0  = *(const uint32_t *)(t + 4);
    uint32_t id56 = *(const uint32_t *)(t + CE_NULL_ROW * CE_ROW_SIZE + 4);
    const char *name56 = *(const char *const *)(t + CE_NULL_ROW * CE_ROW_SIZE);
    if (id0 != 0 || id56 != CE_NULL_ROW) {
        ce_verdict("guard: retail table signature mismatch (row0.id=%u row56.id=%u)", id0, id56);
        return 0;
    }
    if (IsBadReadPtr(name56, 5) || memcmp(name56, "NULL", 5) != 0) {
        ce_verdict("guard: row56.internal_name is not \"NULL\"");
        return 0;
    }
    return 1;
}

int __stdcall thcrap_plugin_init(void)
{
    strcpy(s_logpath, "th18_card_expand.log");
    FILE *f = open_log("w");                       /* 每次启动新开一份 */
    if (f) {
        time_t t = time(NULL);
        char ts[32]; strftime(ts, sizeof ts, "%Y-%m-%d %H:%M:%S", localtime(&t));
        fprintf(f, "=== th18_card_expand %s ===\n", ts);
        fclose(f);
    }
    HMODULE th = GetModuleHandleA("thcrap.dll");
    if (th) {
        s_log_printf = (void (*)(const char *, ...))GetProcAddress(th, "log_printf");
        ce_func_get  = (uintptr_t (*)(const char *))GetProcAddress(th, "func_get");
    }
    ce_log("thcrap exports: log_printf=%s func_get=%s",
           s_log_printf ? "ok" : "MISSING", ce_func_get ? "ok" : "MISSING");
    if (s_log_printf) s_log_printf("[th18_card_expand] loaded; log -> %s\n", s_logpath);

    if (!retail_table_looks_right((const uint8_t *)GetModuleHandleA(NULL))) {
        ce_verdict("guard: not th18 v1.00a as expected — unloading myself");
        return 1;                                   /* 非 0 = 让 thcrap 卸掉本 DLL */
    }
    ce_log("guard: retail table signature ok");
    return 0;
}

/* 名字里 _mod_ 之后是 post_init → mod_func_run_all("post_init") 会调它。
 * 签名按 mod_call_type = void (TH_CDECL*)(void*)（plugin.h:71）。*/
void __cdecl th18_card_expand_mod_post_init(void *param)
{
    (void)param;
    ce_selfcheck_post_init((uint8_t *)GetModuleHandleA(NULL));
}
