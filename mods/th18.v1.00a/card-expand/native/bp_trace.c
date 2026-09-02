/* bp_trace.c —— 测试用断点：记录每次 allocate_new_card(id, mode)。
 *
 * 挂在 0x411469（序言 `cmp [edi+0x28], 0x100`，7 字节），此时 push ebp; mov ebp,esp
 * 已执行：[ebp+8] = card_id，[ebp+0xc] = mode。只读、只记日志、返回 1 照常执行。
 * 只在 patch-test 进栈时才被挂上；正式 patch 不声明这个断点。
 *
 * 跑在游戏线程上下文里：不碰 x87（-mfpmath=sse），不调 thcrap API。
 */
#include "card_expand.h"
#include "thcrap_bp.h"

int __cdecl BP_ce_trace_alloc(x86_reg_t *regs, void *bp_info)
{
    (void)bp_info;
    const uint32_t *frame = (const uint32_t *)(uintptr_t)regs->ebp;
    uint32_t id = frame[2], mode = frame[3];
    if (id >= 57)
        ce_log("trace: allocate_new_card(id=%u, mode=%u)  <- NEW ID", id, mode);
    else
        ce_log("trace: allocate_new_card(id=%u, mode=%u)", id, mode);
    return BP_EXEC_ORIGINAL;
}
