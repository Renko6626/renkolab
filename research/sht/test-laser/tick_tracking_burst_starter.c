/* =============================================================================
 * tick_tracking_burst_starter — 简化起步版(无激光束,只验证 追踪+脉冲+伤害)
 * -----------------------------------------------------------------------------
 * 行为:子弹每帧锁定半径 256px 内最近敌人,硬瞄(角→敌),引擎按 .sht 速度自动飞;
 *       存活 BURST_FRAMES 帧后自我了结(消失)。伤害自动(findings/08,spawn 自带 +0xb0 源)。
 * 落地:编进 code cave,thcrap 重指 tick 表 idx4 槽(0x4919b0)→ 此函数。
 * 配套 .sht:files/pl02_tracklaser.sht(子机弹 init=3,tick=4,hit=0,dmg=30)。
 * 调用约定:__fastcall(self 在 ECX),返回 undefined4。
 *   ★ 返回 0 → tick_bullets 跑默认引擎运动(按 slot+0x60/+0x64 移动);
 *     返回非 0 → tick_bullets 跳过默认运动(我们了结时用,避免对已释放槽再处理)。
 * 性质:规格级 C,地址全部一手坐实(本会话 0x445ee0 反汇编 / list_names)。需编译/手汇编成 cave。
 *       仅 TH16 v1.00a。日期 2026-06-11。
 * ========================================================================== */
#include <stdint.h>

/* ---- 全局 / 函数(一手坐实地址)---- */
#define ENEMY_MANAGER   (*(int*)0x4a6dc0)
#define PLAYER_PTR      (*(int*)0x4a6ef8)
#define HOMING_RADIUS   (*(float*)0x494680)   /* = 256.0,寻的同款 find_nearest 半径 */
/* ★ 调用约定(审计核实 2026-06-11):这三个是 STDCALL(callee 清栈:RET 8 / RET 4 / RET 4),
 *   不是 cdecl —— asm 里调用后**绝不能** add esp(否则破坏 ESP→esi/edi→崩 tick_bullets)。 */
/* find_nearest_enemy(out, &refpos):__stdcall,半径走 XMM3,调用后 *out = 敌句柄(0=无) */
extern void  __stdcall find_nearest_enemy(int* out, float* refpos);  /* 0x425240 RET 8 */
extern int   __stdcall is_enemy_alive(int handle);                   /* 0x41a980 RET 4 */
extern int   __fastcall handle_to_enemy(int* phandle);               /* 0x41b540 ECX=&句柄 → 敌ptr */
extern double crt_atan2_fpu(double dy, double dx);                    /* 0x487aaa FPU,ST0=atan2(dy,dx) */
extern void  __stdcall anm_unload(uint32_t anm_id);                  /* 0x46f1c0 RET 4 */

/* ---- slot 偏移 ---- */
#define LIFE 0x10
#define ANM  0x08
#define X    0x48
#define Y    0x4c
#define ANG  0x64
#define STATE 0x8c
#define TGT  0x90
#define LINK 0xb0
/* enemy */
#define E_X 0x1250
#define E_Y 0x1254
#define E_FLAGS 0x526c   /* & 0xc000021 = 死/无敌/不可锁 */

#define BURST_FRAMES 24

uint32_t __fastcall tick_tracking_burst_starter(int self)
{
    /* (0) 爆发寿命到 → 了结(清伤害源 active 位 + 卸 anm + 释放槽),返回非 0 跳过默认处理 */
    if (*(int*)(self + LIFE) > BURST_FRAMES) {
        int link = *(int*)(self + LINK);
        if (link != 0) {
            uint32_t* obj = (uint32_t*)(PLAYER_PTR + 0xd080 + link * 0x94);
            *obj &= 0xfffffffe;            /* 伤害源 active bit0 清,停止掉血 */
        }
        anm_unload(*(uint32_t*)(self + ANM));
        *(int*)(self + ANM)   = 0;
        *(int*)(self + STATE) = 0;          /* 槽释放(下一帧 tick_bullets 视为空) */
        return 1;                            /* 跳过默认运动/拷贝 */
    }

    /* (1) 锁敌:无目标则找最近;丢失则清。slot+0x90 由 init=3 起始清 0 */
    {
        int* tgt = (int*)(self + TGT);
        if (ENEMY_MANAGER == 0) {
            *tgt = 0;
        } else if (*tgt == 0) {
            int handle = 0;
            float ref[2] = { *(float*)(self + X), *(float*)(self + Y) };
            /* 半径 HOMING_RADIUS 经 XMM3 传入(见 asm);out=&handle */
            find_nearest_enemy(&handle, ref);
            *tgt = handle;
        }
        if (*tgt != 0) {
            if (!is_enemy_alive(*tgt)) {
                *tgt = 0;
            } else {
                int enemy = handle_to_enemy(tgt);   /* ECX = tgt(=&slot+0x90) */
                if ((*(uint32_t*)(enemy + E_FLAGS) & 0xc000021) == 0) {
                    /* (2) 硬瞄:角 = atan2(dy, dx),引擎按此角+速度自动飞向敌人 */
                    float dy = *(float*)(enemy + E_Y) - *(float*)(self + Y);
                    float dx = *(float*)(enemy + E_X) - *(float*)(self + X);
                    *(float*)(self + ANG) = (float)crt_atan2_fpu(dy, dx);
                }
            }
        }
    }
    /* (3) 伤害:免写(findings/08)。返回 0 → 引擎按 slot+0x60 速度 / +0x64 角移动子弹,
     *     tick_bullets 把新位置拷进 +0xb0 伤害源,敌人侧自动判重叠扣血(数值=.sht dmg)。*/
    return 0;
}
