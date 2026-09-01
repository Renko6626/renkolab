/*
 * bp_mouse.c —— BP_mouse_move:把光标方位合成成 INPUT_HELD 的方向位。
 *
 * 挂在 Player__sub_45b170 入口(见 mouse-control/patch/th18.v1.00a.js)。
 *
 * ★ 设计要点:**只写 INPUT_HELD 一个 dword,玩家对象零写入。**
 *   钳位、子机跟随轨迹、倾斜动画、外力位移全部由游戏自己的代码完成 ——
 *   我们只是替它决定「这一帧按了哪个方向」。所以本模块不碰 ABI、不碰栈、
 *   不调引擎函数,AUDIT-checklist 的 A 节整节不适用。
 *
 * 数学一律走整数。唯一的浮点是速度倍率那一次乘法,而且倍率 == 1.0f 时跳过 ——
 * 这样常规路径上一条浮点指令都没有,不可能扰动游戏的 FPU/SSE 状态。
 */

#include <windows.h>
#include <stdint.h>
#include <string.h>

#include "th18.h"
#include "thcrap_bp.h"

/* tan(22.5°) = 0.414214 —— 八向量化的扇区边界,用整数比例表示 */
#define TAN225_NUM   414214
#define TAN225_DEN  1000000

#define TOGGLE_VK    VK_F9

static int g_on;            /* 鼠标控制是否激活 */
static int g_cursor_hidden;
static int g_disabled;      /* 遇到不支持的情形后永久停用(只记一次日志) */

/* ---- 一次性诊断 ----
 * 断点每帧跑一次,直接打日志会刷屏。每条路径只记一次,一趟运行就能看出
 * 卡在哪个边界:没有 "[diag] 首次触发" = 断点压根没挂上(去查 thcrap 自己的日志);
 * 有首次触发但停在某条提前返回上 = 那一处的假设错了。 */
static int d_entry, d_nohwnd, d_badptr, d_flags, d_cursor, d_ok;
static int d_btn_entry, d_btn_ok;

#define ONCE(flag, ...) do { if (!(flag)) { (flag) = 1; rk_log(__VA_ARGS__); } } while (0)

/* ------------------------------------------------------------------ */

static void set_cursor_hidden(int hide)
{
    if (hide == g_cursor_hidden) return;
    ShowCursor(hide ? FALSE : TRUE);   /* 计数式 API,保证成对调用 */
    g_cursor_hidden = hide;
}

/* F9 上升沿(仅在游戏窗口是前台时响应) */
static void poll_toggle(HWND hwnd)
{
    if (GetForegroundWindow() != hwnd) return;
    if (GetAsyncKeyState(TOGGLE_VK) & 1) {
        g_on = !g_on;
        rk_log("[mouse] %s", g_on ? "开" : "关");
        if (!g_on) set_cursor_hidden(0);
    }
}

static int clampi(int v, int lo, int hi)
{
    return v < lo ? lo : (v > hi ? hi : v);
}

/* ------------------------------------------------------------------ */

size_t __cdecl BP_mouse_move(x86_reg_t *regs, void *bp_info)
{
    uint8_t *p;
    HWND hwnd;
    POINT pt;
    RECT rc;
    int cw, ch, focus, speed, S, tgt_x, tgt_y, dx, dy, ax, ay;
    uint32_t multbits, bits, *held;
    long long d2;

    (void)bp_info;

    ONCE(d_entry, "[diag] BP_mouse_move 首次触发 ecx=%p", (void *)regs->ecx);

    if (g_disabled) return BP_EXEC_ORIGINAL;

    hwnd = *(HWND *)(g_base + RVA_SUPERVISOR + OFF_SV_HWND);
    if (!hwnd || !IsWindow(hwnd)) {
        ONCE(d_nohwnd, "[diag] main_window=%p IsWindow=%d —— 提前返回",
             (void *)hwnd, hwnd ? IsWindow(hwnd) : 0);
        return BP_EXEC_ORIGINAL;
    }

    poll_toggle(hwnd);
    if (!g_on) return BP_EXEC_ORIGINAL;

    /* this 在 ECX(Player__sub_45b170 是 __fastcall 单参)。
     * 与全局 PLAYER_PTR 交叉核对 —— 对不上说明我们挂错了地方,立刻放行。 */
    p = (uint8_t *)regs->ecx;
    if (!p || p != *(uint8_t **)(g_base + RVA_PLAYER_PTR)) {
        ONCE(d_badptr, "[diag] ecx=%p 与 PLAYER_PTR=%p 不等 —— 提前返回",
             (void *)p, *(void **)(g_base + RVA_PLAYER_PTR));
        return BP_EXEC_ORIGINAL;
    }

    /* (flags & 0x180) != 0 时游戏走的是入场/死亡动画分支,不读方向位。
     * 那时插手没有意义,而且会让动画期间的状态变得难以推理。 */
    if ((*(uint32_t *)(p + OFF_FLAGS) & 0x180u) != 0) {
        ONCE(d_flags, "[diag] flags=0x%x & 0x180 != 0 —— 提前返回(入场/死亡动画)",
             *(uint32_t *)(p + OFF_FLAGS));
        return BP_EXEC_ORIGINAL;
    }

    /* ---- 屏幕坐标 → 游戏亚像素坐标 ---- */
    if (!GetCursorPos(&pt) || !ScreenToClient(hwnd, &pt)) {
        ONCE(d_cursor, "[diag] GetCursorPos/ScreenToClient 失败 err=%lu —— 提前返回",
             GetLastError());
        return BP_EXEC_ORIGINAL;
    }
    if (!GetClientRect(hwnd, &rc)) {
        ONCE(d_cursor, "[diag] GetClientRect 失败 err=%lu —— 提前返回", GetLastError());
        return BP_EXEC_ORIGINAL;
    }
    cw = rc.right;
    ch = rc.bottom;
    if (cw <= 0 || ch <= 0) return BP_EXEC_ORIGINAL;

    /* 自机/弹幕画在 640x480 的 surface 上,再整体缩放到窗口 —— 所以客户区必须是 4:3。
     * 不是的话(全屏黑边等)我们的换算就是错的,宁可停用也不给一个偏掉的结果。 */
    if (cw * 3 != ch * 4) {
        rk_log("[mouse] 客户区 %dx%d 不是 4:3,换算不成立,永久停用。", cw, ch);
        g_disabled = 1;
        g_on = 0;
        set_cursor_hidden(0);
        return BP_EXEC_ORIGINAL;
    }

    /* 客户区像素 → 640x480 虚拟像素 → 减去游戏区原点 → ×128 变亚像素。
     * 合成一步做完以保精度;用 long long 防中间量溢出。 */
    tgt_x = (int)(((long long)pt.x * VIRT_W * SUBPIXEL) / cw) - PLAYFIELD_CX * SUBPIXEL;
    tgt_y = (int)(((long long)pt.y * VIRT_H * SUBPIXEL) / ch) - PLAYFIELD_TOP * SUBPIXEL;

    /* 钳到游戏自己的边界:光标移出弹幕区时,自机停在对应的墙上并进入死区,
     * 而不是永远朝墙按着。 */
    tgt_x = clampi(tgt_x, -CLAMP_X_ABS, CLAMP_X_ABS);
    tgt_y = clampi(tgt_y, CLAMP_Y_MIN, CLAMP_Y_MAX);

    dx = tgt_x - *(int *)(p + OFF_SUB_X);
    dy = tgt_y - *(int *)(p + OFF_SUB_Y);

    /* ---- 本帧的合法步长 S(亚像素) ---- */
    /* 低速位读 INPUT_HELD 而不是 p+0x476cc:后者由本函数在我们的 hook 点**之后**
     * 才写入,现在读到的是上一帧的值,按下 Shift 的那一帧会用错速度。 */
    held = (uint32_t *)(g_base + RVA_INPUT_HELD);
    focus = ((*held & IN_FOCUS) != 0);
    speed = *(int *)(p + (focus ? OFF_SPD_F_CARD : OFF_SPD_U_CARD));
    multbits = *(uint32_t *)(p + OFF_SPEED_MULT);
    S = speed;
    if (multbits != 0x3f800000u) {          /* != 1.0f 才动浮点 */
        float m;
        memcpy(&m, &multbits, sizeof(m));
        S = (int)((float)speed * m);
    }
    if (S <= 0) return BP_EXEC_ORIGINAL;    /* 定身/无法移动,别插手 */

    /* ---- 死区:够不上一步就不动,否则会在光标附近来回震荡 ---- */
    d2 = (long long)dx * dx + (long long)dy * dy;
    if (d2 < (long long)S * S) {
        bits = 0;
    }
    else {
        /* 八向量化,纯整数:|dy| < |dx|·tan22.5° → 纯水平,反之纯垂直,否则斜向。
         * 游戏 y 轴向下(顶边 32、底边 432),所以 dy > 0 = 目标在下方 = 按「下」。 */
        ax = dx < 0 ? -dx : dx;
        ay = dy < 0 ? -dy : dy;
        if ((long long)ay * TAN225_DEN < (long long)ax * TAN225_NUM) {
            bits = (dx > 0) ? IN_RIGHT : IN_LEFT;
        }
        else if ((long long)ax * TAN225_DEN < (long long)ay * TAN225_NUM) {
            bits = (dy > 0) ? IN_DOWN : IN_UP;
        }
        else {
            bits = ((dx > 0) ? IN_RIGHT : IN_LEFT) | ((dy > 0) ? IN_DOWN : IN_UP);
        }
    }

    ONCE(d_ok, "[diag] 首次生效 client=%dx%d cursor=(%ld,%ld) tgt=(%d,%d) pos=(%d,%d) S=%d focus=%d",
         cw, ch, pt.x, pt.y, tgt_x, tgt_y,
         *(int *)(p + OFF_SUB_X), *(int *)(p + OFF_SUB_Y), S, focus);

    /* ---- 唯一的一次写:只动方向位,其余位(射击/炸弹/低速/用卡)原样保留 ---- */
    *held = (*held & ~IN_DIR_MASK) | bits;

    set_cursor_hidden(1);
    return BP_EXEC_ORIGINAL;
}

/* ------------------------------------------------------------------ *
 * BP_mouse_buttons —— 左键 = 射击(Z)，右键 = 炸弹(X)，中键 = 用卡(C)
 *
 * 挂在 ReplayManager__on_tick__record_replay 里 `call Input__compute_edges`
 * 那一条(0x462966)上。**位置是被迫的，不是随便挑的**:
 *
 *     _INPUT_HELD_PREV = INPUT_HELD;
 *     INPUT_HELD = DAT_004ca210;      // 原始输入
 *     Input__compute_edges();         // ← 我们在这条之前注入
 *     ...
 *     FUN_00463060(chunk, INPUT_HELD, INPUT_PRESSED, INPUT_RELEASED);  // 写进 replay
 *
 * 炸弹读的是 `INPUT_PRESSED & 2`、用卡读的是 `INPUT_PRESSED & 0x400`(都是上升沿)，
 * 而上升沿就在这条 call 里算出来。注入晚一步这两个键就永远不产生边沿 ——
 * 炸弹和用卡一次都放不出来。
 *
 * 两个顺带的性质:
 *   · 记录 replay 的 0x463060 在我们之后 → 鼠标输入会一致地录进录像。
 *   · 这是**录制**那条 on_tick;回放走 0x462a50，我们碰不到 → 看录像时自动失效。
 *
 * 与方向位不同:按键只 **OR**、从不清位,所以键盘 Z/X 照常可用,鼠标只是多一路来源。
 * ------------------------------------------------------------------ */

size_t __cdecl BP_mouse_buttons(x86_reg_t *regs, void *bp_info)
{
    HWND hwnd;
    uint32_t *held, add = 0;

    (void)regs;
    (void)bp_info;

    ONCE(d_btn_entry, "[diag] BP_mouse_buttons 首次触发");

    if (!g_on || g_disabled) return BP_EXEC_ORIGINAL;

    /* 只在游戏是前台时接管,否则 alt-tab 出去点别的窗口会照样开火 */
    hwnd = *(HWND *)(g_base + RVA_SUPERVISOR + OFF_SV_HWND);
    if (!hwnd || GetForegroundWindow() != hwnd) return BP_EXEC_ORIGINAL;

    if (GetAsyncKeyState(VK_LBUTTON) & 0x8000) add |= IN_SHOOT;
    if (GetAsyncKeyState(VK_RBUTTON) & 0x8000) add |= IN_BOMB;
    if (GetAsyncKeyState(VK_MBUTTON) & 0x8000) add |= IN_CARD;
    if (!add) return BP_EXEC_ORIGINAL;

    held = (uint32_t *)(g_base + RVA_INPUT_HELD);
    *held |= add;

    ONCE(d_btn_ok, "[diag] 鼠标按键首次生效 add=0x%x", add);
    return BP_EXEC_ORIGINAL;
}
