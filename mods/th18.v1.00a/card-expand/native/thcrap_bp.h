/*
 * thcrap_bp.h —— thcrap breakpoint ABI 的最小复刻。
 *
 * 刻意**不链接 thcrap 导入库**:BP 函数只要不调 thcrap 的 API,就只需要
 * x86_reg_t 的布局正确。少一个依赖 = 少一类构建与版本漂移问题。
 *
 * 布局出处:thcrap/src/expression.h:73-158(@ e2e315e)。x86 上它就是一个
 * pushad 帧 + 返回地址 —— pushad 的压栈顺序是 eax,ecx,edx,ebx,esp,ebp,esi,edi,
 * 所以内存里从低到高正好是 edi,esi,ebp,esp,ebx,edx,ecx,eax。
 *
 * ⚠️ 字段顺序错一位,读到的就是另一个寄存器,且不会报错。改这里必须回去比对源码。
 */

#ifndef THCRAP_BP_H
#define THCRAP_BP_H

#include <stdint.h>

typedef struct {
    uint32_t eflags;        /* ★ 别删:x86 下结构体的第一个字段就是它 */
    uint32_t edi;
    uint32_t esi;
    uint32_t ebp;
    uint32_t esp;
    uint32_t ebx;
    uint32_t edx;
    uint32_t ecx;
    uint32_t eax;
    uint32_t retaddr;
} x86_reg_t;

/*
 * 断点函数返回值(thcrap/src/breakpoint.h:26-30):
 *   1 = 执行被挪进 cave 的原指令(正常放行)
 *   0 = 不执行原指令;此时可以改 regs->retaddr 让执行从别处继续
 * 我们一律返回 1 —— 本 DLL 不改变任何控制流。
 */
#define BP_EXEC_ORIGINAL 1

/* 共用:模块基址(GetModuleHandleW(NULL)),由 dll_main.c 在 init 时填好 */
extern uint8_t *g_base;

/* 共用:写一行日志(自带换行与 flush);未开日志时是空操作 */
void rk_log(const char *fmt, ...);

#endif /* THCRAP_BP_H */
