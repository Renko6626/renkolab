/*
 * dll_main.c —— th18_mouse thcrap 插件:入口、版本守卫、日志。
 */

#include <windows.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>

#include "th18.h"
#include "thcrap_bp.h"

uint8_t *g_base;

static FILE *g_log;

/* ------------------------------------------------------------------ */

void rk_log(const char *fmt, ...)
{
    va_list ap;
    if (!g_log) return;
    va_start(ap, fmt);
    vfprintf(g_log, fmt, ap);
    va_end(ap);
    fputc('\n', g_log);
    fflush(g_log);              /* 崩了也要留下最后一行 */
}

/* ------------------------------------------------------------------ */

/* 与 runtime-probe 同源的两处 .text 签名。不匹配 = 不是 th18 v1.00a。 */
static const BYTE SIG_A[] = {
    0x55, 0x8b, 0xec, 0x83, 0xe4, 0xf0, 0xf3, 0x0f,
    0x10, 0x1d, 0x74, 0x91, 0x4b, 0x00, 0x83, 0xec
};
static const BYTE SIG_B[] = {
    0x83, 0x3d, 0xa4, 0xf2, 0x4c, 0x00, 0x00, 0x74,
    0x06, 0xb8, 0x01, 0x00, 0x00, 0x00, 0xc3, 0xe9
};

static BOOL readable(const void *p, SIZE_T len)
{
    MEMORY_BASIC_INFORMATION mbi;
    const BYTE *cur = (const BYTE *)p;
    const BYTE *end = cur + len;

    if (!p) return FALSE;
    while (cur < end) {
        if (!VirtualQuery(cur, &mbi, sizeof(mbi))) return FALSE;
        if (mbi.State != MEM_COMMIT) return FALSE;
        if (mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD)) return FALSE;
        if (!(mbi.Protect & (PAGE_READONLY | PAGE_READWRITE | PAGE_WRITECOPY |
                             PAGE_EXECUTE_READ | PAGE_EXECUTE_READWRITE |
                             PAGE_EXECUTE_WRITECOPY)))
            return FALSE;
        cur = (const BYTE *)mbi.BaseAddress + mbi.RegionSize;
    }
    return TRUE;
}

static BOOL sig_matches(DWORD rva, const BYTE *sig, SIZE_T len, const char *what)
{
    const BYTE *at = g_base + rva;
    if (!readable(at, len)) {
        rk_log("[guard] %s @ base+0x%lx 不可读", what, rva);
        return FALSE;
    }
    if (memcmp(at, sig, len) != 0) {
        rk_log("[guard] %s @ base+0x%lx 原字节不匹配 —— 不是 th18.v1.00a", what, rva);
        rk_log("[guard]   期望 %02x %02x %02x %02x ... 实读 %02x %02x %02x %02x ...",
               sig[0], sig[1], sig[2], sig[3], at[0], at[1], at[2], at[3]);
        return FALSE;
    }
    return TRUE;
}

/* ------------------------------------------------------------------ */

int __stdcall thcrap_plugin_init(void)
{
    char exe[MAX_PATH], log_path[MAX_PATH];
    char *slash;
    SYSTEMTIME st;

    g_base = (uint8_t *)GetModuleHandleW(NULL);
    if (!GetModuleFileNameA(NULL, exe, MAX_PATH)) return 1;

    lstrcpynA(log_path, exe, MAX_PATH);
    slash = strrchr(log_path, '\\');
    lstrcpynA(slash ? slash + 1 : log_path, "th18_mouse.log",
              MAX_PATH - (int)(slash ? slash + 1 - log_path : 0));
    g_log = fopen(log_path, "a");
    if (!g_log) {
        /* 游戏装在只读位置时退到 %TEMP%,否则会「加载了但什么也没有」 */
        DWORD n = GetTempPathA(MAX_PATH, log_path);
        if (n == 0 || n >= MAX_PATH - 16) return 1;
        lstrcatA(log_path, "th18_mouse.log");
        g_log = fopen(log_path, "a");
    }

    GetLocalTime(&st);
    rk_log("");
    rk_log("=== th18_mouse 起 %04d-%02d-%02d %02d:%02d:%02d ===",
           st.wYear, st.wMonth, st.wDay, st.wHour, st.wMinute, st.wSecond);
    rk_log("exe  = %s", exe);
    rk_log("base = %p", (void *)g_base);

    if (!sig_matches(RVA_SIG_A, SIG_A, sizeof(SIG_A), "Player__sub_45b170") ||
        !sig_matches(RVA_SIG_B, SIG_B, sizeof(SIG_B), "Player__on_tick")) {
        rk_log("[guard] 校验失败,插件自我卸载(thcrap 会 FreeLibrary)。");
        if (g_log) { fclose(g_log); g_log = NULL; }
        return 1;   /* 非 0 = 卸载我 */
    }
    rk_log("[guard] 两处 .text 签名匹配,确认 th18.v1.00a。");
    rk_log("BP_mouse_move 就绪(F9 开关鼠标控制)");
    return 0;       /* 0 = 留下 */
}

/* thcrap 关闭时调用(导出名后缀 _mod_exit;init.cpp:459 在 FreeLibrary 之前) */
void __cdecl th18_mouse_mod_exit(void *param)
{
    (void)param;
    if (g_log) {
        rk_log("=== th18_mouse 止 ===");
        fclose(g_log);
        g_log = NULL;
    }
}

BOOL WINAPI DllMain(HINSTANCE inst, DWORD reason, LPVOID reserved)
{
    (void)reserved;
    if (reason == DLL_PROCESS_ATTACH) DisableThreadLibraryCalls(inst);
    return TRUE;
}
