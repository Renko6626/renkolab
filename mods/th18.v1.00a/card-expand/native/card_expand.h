/* card_expand.h —— th18_card_expand.dll 内部共用的声明。
 *
 * 这个 DLL 是 card-expand mod 的唯一 DLL。职责按文件分：
 *   dll_main.c    入口 / 日志 / thcrap API 解析 / 开机自检①（零售表签名）
 *   selfcheck.c   开机自检②：post_init 里填表 + 回读 100 处 + 写结论
 *   （后续）       分配器桩注册、数据激活门 …
 */
#pragma once
#include <windows.h>
#include <stdint.h>
#include "sites_gen.h"

/* 日志：优先进 thcrap 自己的日志；拿不到 log_printf 时退到文件 */
void ce_log(const char *fmt, ...);

/* thcrap 导出（GetProcAddress 取得，可能为 NULL） */
extern uintptr_t (*ce_func_get)(const char *);

/* 开机自检②：填表 + 回读验证。返回 1 = 通过 */
int ce_selfcheck_post_init(uint8_t *module_base);
