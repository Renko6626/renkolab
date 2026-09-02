/* card_expand.h —— th18_card_expand.dll 内部共用的声明。
 *
 * 这个 DLL 是 card-expand mod 的唯一 DLL。职责按文件分：
 *   dll_main.c    入口 / 日志文件 / thcrap API 解析 / 开机自检①（零售表签名）
 *   selfcheck.c   开机自检②：BP_ce_gate 里填表（+跳转表）+ 回读站点 + 写结论
 *   unlocked.c    战线 D：unlocked_cards 影子数组 + side-car；三个断点
 *   bp_trace.c    测试用断点：记录每次 allocate_new_card(id, mode)，新 id 顺手 mark_obtained（只在 patch-test 进栈时挂）
 *   （后续）       数据激活门、新卡注册 …
 */
#pragma once
#include <windows.h>
#include <stdint.h>
#include "sites_gen.h"

/* 日志：一律写自己的文件 th18_card_expand.log（游戏目录，写不了退到 %TEMP%）。
 * ce_verdict 额外把那一行镜像进 thcrap 的日志——只镜像结论，不刷屏。*/
void ce_log(const char *fmt, ...);
void ce_verdict(const char *fmt, ...);

/* thcrap 导出（GetProcAddress 取得，可能为 NULL） */
extern uintptr_t (*ce_func_get)(const char *);

/* 日志所在目录（游戏 exe 目录，尾带反斜杠）—— side-car 的兜底位置 */
void ce_log_dir(char *out, size_t cap);

/* 开机自检②（由 BP_ce_gate 调一次）。返回 1 = 通过 */
int ce_selfcheck(uint8_t *module_base);

/* 战线 D（unlocked.c）：找影子 codecave（NULL = 不在栈里）；核对 9 处读 + 3 个断点 */
uint8_t *ce_unlock_init(uint8_t *module_base);
int ce_unlock_check(uint8_t *module_base);
