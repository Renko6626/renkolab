/*
 * th18_probe —— TH18 v1.00a 只读运行时探针（thcrap 插件）
 *
 * 只读：不往游戏内存写任何字节，不装 binhack / breakpoint / codecave。
 * 唯一作用是每 POLL_MS 毫秒读一次 PLAYER_PTR 指向的 zPlayer，把坐标与两个
 * 状态位追加进游戏目录下的 th18_probe.log。
 *
 * 地址与偏移的出处见同目录 ../TARGET.md，语义出处见
 * engine/player/th18/01-position-and-state-timers.md。
 * 换 exe build 这些量全部作废 —— 所以有 §签名校验，不匹配即自我卸载。
 */

#include <windows.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <math.h>

/* ---- 死绑 TH18 v1.00a（th18.exe md5 9969cac756098c1da05a81de45437a70）---- */

#define RVA_SIG_A        0x5b170u   /* Player__sub_45b170  (VA 0x45b170) */
#define RVA_SIG_B        0x5caa0u   /* Player__on_tick     (VA 0x45caa0) */
#define RVA_PLAYER_PTR   0xcf410u   /* PLAYER_PTR : zPlayer* (VA 0x4cf410) */

static const BYTE SIG_A[] = {
    0x55, 0x8b, 0xec, 0x83, 0xe4, 0xf0, 0xf3, 0x0f,
    0x10, 0x1d, 0x74, 0x91, 0x4b, 0x00, 0x83, 0xec
};
static const BYTE SIG_B[] = {
    0x83, 0x3d, 0xa4, 0xf2, 0x4c, 0x00, 0x00, 0x74,
    0x06, 0xb8, 0x01, 0x00, 0x00, 0x00, 0xc3, 0xe9
};

/* zPlayer 内偏移（engine/player/th18/01 §1，✅ 一手） */
#define OFF_POS_X        0x620u     /* float, px */
#define OFF_POS_Y        0x624u
#define OFF_POS_Z        0x628u
#define OFF_SUB_X        0x62cu     /* int, 1/128 px 定点（权威副本） */
#define OFF_SUB_Y        0x630u
#define OFF_STATE        0x476acu   /* int, Player__on_tick__body 的 switch 0-4 */
#define OFF_FOCUS        0x476ccu   /* int, INPUT_HELD >> 3 & 1 */

/* 自校验判据（同文 §2③）：x 钳位 ±0x5c00 → ±184 px；y ∈ [0x1000,0xd800] → [32,432] px */
#define X_ABS_MAX        184.0f
#define Y_MIN            32.0f
#define Y_MAX            432.0f

#define POLL_MS          100
#define HEARTBEAT_MS     5000

static HANDLE   g_thread;
static volatile LONG g_running;
static FILE    *g_log;
static BYTE    *g_base;

/* ------------------------------------------------------------------ */

static void probe_log(const char *fmt, ...)
{
    va_list ap;
    if (!g_log) return;
    va_start(ap, fmt);
    vfprintf(g_log, fmt, ap);
    va_end(ap);
    fputc('\n', g_log);
    fflush(g_log);              /* 崩了也要留下最后一行 */
}

/* 读之前先问操作系统这段地址能不能读 —— PLAYER_PTR 在关卡切换时可能是野值。
 * 用 VirtualQuery 而不是 __try/__except：i686 上的 SEH 在 clang 里不可靠。 */
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
        probe_log("[guard] %s @ base+0x%lx 不可读 —— 不是预期的 exe", what, rva);
        return FALSE;
    }
    if (memcmp(at, sig, len) != 0) {
        probe_log("[guard] %s @ base+0x%lx 原字节不匹配 —— 不是 th18.v1.00a", what, rva);
        probe_log("[guard]   期望 %02x %02x %02x %02x ... 实读 %02x %02x %02x %02x ...",
                  sig[0], sig[1], sig[2], sig[3], at[0], at[1], at[2], at[3]);
        return FALSE;
    }
    return TRUE;
}

/* ------------------------------------------------------------------ */

static DWORD WINAPI poll_thread(LPVOID unused)
{
    float  last_x = -1e30f, last_y = -1e30f;
    int    last_state = -1, last_focus = -1;
    DWORD  t0 = GetTickCount(), last_beat = 0;
    BOOL   had_player = FALSE;

    (void)unused;

    while (InterlockedCompareExchange(&g_running, 1, 1)) {
        BYTE **slot = (BYTE **)(g_base + RVA_PLAYER_PTR);
        BYTE  *player;
        DWORD  now = GetTickCount() - t0;

        if (readable(slot, sizeof(BYTE *)) && (player = *slot) != NULL &&
            readable(player + OFF_POS_X, 12) &&
            readable(player + OFF_STATE, 4) &&
            readable(player + OFF_FOCUS, 4)) {

            float x = *(float *)(player + OFF_POS_X);
            float y = *(float *)(player + OFF_POS_Y);
            float z = *(float *)(player + OFF_POS_Z);
            int  sx = *(int *)(player + OFF_SUB_X);
            int  sy = *(int *)(player + OFF_SUB_Y);
            int  st = *(int *)(player + OFF_STATE);
            int  fc = *(int *)(player + OFF_FOCUS);

            BOOL moved   = (x != last_x) || (y != last_y);
            BOOL changed = (st != last_state) || (fc != last_focus);
            BOOL beat    = (now - last_beat) >= HEARTBEAT_MS;

            if (!had_player) {
                probe_log("[%7u ms] PLAYER_PTR = %p （出现）", now, (void *)player);
                had_player = TRUE;
            }
            if (moved || changed || beat) {
                /* 自校验：坐标是否落在 §2③ 推出的弹幕区范围里 */
                const char *verdict =
                    (x >= -X_ABS_MAX && x <= X_ABS_MAX && y >= Y_MIN && y <= Y_MAX)
                    ? "IN-RANGE" : "OUT-OF-RANGE";
                /* 交叉校验：float 坐标应当 == 定点值 / 128 */
                float rx = (float)sx / 128.0f, ry = (float)sy / 128.0f;
                const char *coherent =
                    (fabsf(rx - x) < 0.01f && fabsf(ry - y) < 0.01f) ? "ok" : "MISMATCH";

                probe_log("[%7u ms] x=%8.2f y=%8.2f z=%6.2f | sub=(%7d,%7d) /128 -> (%8.2f,%8.2f) %s"
                          " | focus=%d state=%d | %s",
                          now, x, y, z, sx, sy, rx, ry, coherent, fc, st, verdict);

                last_x = x; last_y = y; last_state = st; last_focus = fc;
                last_beat = now;
            }
        }
        else if (had_player) {
            probe_log("[%7u ms] PLAYER_PTR 变为空/不可读（离开关卡？）", now);
            had_player = FALSE;
            last_beat = now;
        }
        else if ((now - last_beat) >= HEARTBEAT_MS) {
            probe_log("[%7u ms] 等待 PLAYER_PTR ...", now);
            last_beat = now;
        }

        Sleep(POLL_MS);
    }
    return 0;
}

/* ------------------------------------------------------------------ */

int __stdcall thcrap_plugin_init(void)
{
    char exe[MAX_PATH], log_path[MAX_PATH];
    char *slash;
    SYSTEMTIME st;

    g_base = (BYTE *)GetModuleHandleW(NULL);
    if (!GetModuleFileNameA(NULL, exe, MAX_PATH)) return 1;

    /* 日志优先与 exe 同目录 */
    lstrcpynA(log_path, exe, MAX_PATH);
    slash = strrchr(log_path, '\\');
    lstrcpynA(slash ? slash + 1 : log_path, "th18_probe.log",
              MAX_PATH - (int)(slash ? slash + 1 - log_path : 0));

    g_log = fopen(log_path, "a");
    if (!g_log) {
        /* 游戏装在 Program Files 之类只读位置时退到 %TEMP%，
         * 否则探针会「加载了但什么也没有」，最难排查的那种失败。 */
        DWORD n = GetTempPathA(MAX_PATH, log_path);
        if (n == 0 || n >= MAX_PATH - 16) return 1;
        lstrcatA(log_path, "th18_probe.log");
        g_log = fopen(log_path, "a");
        if (!g_log) return 1;
    }

    GetLocalTime(&st);
    probe_log("");
    probe_log("=== th18_probe 起 %04d-%02d-%02d %02d:%02d:%02d ===",
              st.wYear, st.wMonth, st.wDay, st.wHour, st.wMinute, st.wSecond);
    probe_log("exe  = %s", exe);
    probe_log("base = %p （imagebase 应为 0x400000，该 exe 无 DYNAMICBASE）", (void *)g_base);

    /* 签名校验 —— 相当于 binhack 的 expected，不匹配就自我卸载 */
    if (!sig_matches(RVA_SIG_A, SIG_A, sizeof(SIG_A), "Player__sub_45b170") ||
        !sig_matches(RVA_SIG_B, SIG_B, sizeof(SIG_B), "Player__on_tick")) {
        probe_log("[guard] 校验失败，探针自我卸载（thcrap 会 FreeLibrary）。");
        fclose(g_log);
        g_log = NULL;
        return 1;
    }
    probe_log("[guard] 两处 .text 签名匹配，确认 th18.v1.00a。");
    probe_log("log  = %s", log_path);
    probe_log("字段：x/y/z=player+0x620/624/628 (float px)，sub=player+0x62c/630 (1/128 px)，"
              "focus=player+0x476cc，state=player+0x476ac");
    probe_log("判据：x∈[-184,184] y∈[32,432] 即 IN-RANGE；float 与定点/128 应一致（ok）。");

    InterlockedExchange(&g_running, 1);
    g_thread = CreateThread(NULL, 0, poll_thread, NULL, 0, NULL);
    if (!g_thread) {
        probe_log("[fatal] CreateThread 失败：%lu", GetLastError());
        InterlockedExchange(&g_running, 0);
        fclose(g_log);
        g_log = NULL;
        return 1;
    }
    return 0;   /* 0 = 留下 */
}

/* thcrap 在关闭时调用所有导出名形如 *_mod_exit 的函数（plugin.h §Module functions） */
void __cdecl probe_mod_exit(void *param)
{
    (void)param;
    InterlockedExchange(&g_running, 0);
    if (g_thread) {
        WaitForSingleObject(g_thread, 1000);
        CloseHandle(g_thread);
        g_thread = NULL;
    }
    if (g_log) {
        probe_log("=== th18_probe 止 ===");
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
