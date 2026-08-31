/* =============================================================================
 * tick_tracking_burst_laser  —  TH16 自机弹「追踪 + 爆发激光」新 tick 函数
 * -----------------------------------------------------------------------------
 * 目标:克隆 idx2 激光,把"方向源"换成瞄准最近敌人,并加爆发寿命。
 * 落地:编进 code cave,thcrap 重指 tick 表 idx4 槽 (0x4919b0) → 此函数。
 * 调用约定:func_on_tick 是 __fastcall(self 在 ECX),返回 undefined4(放 EAX,通常 0)。
 *
 * 性质:这是【规格级 C】(spec),不是 idx2 的逐字节拷贝。所有偏移/地址来自
 *       Ghidra DB `th16` 一手反编译(findings/03)。标 TODO 的项汇编前必须核。
 *       ★★ 伤害路径(见 PLAN §3 开放项 1)尚未反掉 —— 本文件画得出束、瞄得准,
 *          但"是否真造成伤害"未证;先反伤害再信。
 * 版本:仅 TH16 v1.00a (th16.exe, imagebase 0x400000)。日期 2026-06-11。
 * ========================================================================== */

#include <stdint.h>

/* ---- 运行时子弹槽偏移(self = ECX,findings/03 §3 / 05 §2 词汇表)---- */
#define SLOT_LIFETIME   0x10   /* int   存活帧 */
#define SLOT_X          0x48   /* float */
#define SLOT_Y          0x4c   /* float */
#define SLOT_Z          0x50   /* float */
#define SLOT_SPEED      0x60   /* float  (= shooter +0x18) */
#define SLOT_ANGLE      0x64   /* float  移动角 (= shooter +0x14);atan2 结果写这里 */
#define SLOT_ANM_VM     0x08   /* u32    anm vm id */
#define SLOT_STATE      0x8c   /* int    1=活动 / 2=结束(置 2 = 走 idx2 激光熄灭收尾) */
#define SLOT_TARGET     0x90   /* int    寻的目标句柄槽(init 须清 0) */
#define SLOT_CHARGE     0xa0   /* float  激光蓄力/长度,每帧 +18 封顶 512 */
#define SLOT_PACKEDID   0xac   /* u32    (set<<8)|idx;bit 0xf0000 区分主/副 sht */
#define SLOT_POOLLINK   0xb0   /* int    +0xb0 链接的激光池对象索引(0=无) */

/* ---- 全局(findings/03 §3)---- */
#define ENEMY_MANAGER   (*(int*)0x4a6dc0)   /* +0x180=敌链表头 */
#define PLAYER_PTR      (*(int*)0x4a6ef8)   /* 子弹/option 池基址;+0x6bc=option 位置表 */
#define ANM_MANAGER     (*(int*)/*ANM_MANAGER_PTR TODO 确认地址*/0)
#define FOCUS_FLAG      (*(int*)(PLAYER_PTR + 0x165c8))  /* 🟡 非0=聚焦(findings/07) */

/* ---- 敌人结构 ---- */
#define ENEMY_X  0x1250
#define ENEMY_Y  0x1254
#define ENEMY_FLAGS 0x526c    /* & 0xc000021 = 死亡/无敌/不可锁定 */

/* ---- 复用的引擎函数(一手定位,findings/03)---- */
/* find_nearest_enemy(out, &refpos{x,y});半径走 XMM3。返回 ptr,*ptr = 敌句柄。TODO: 半径/ABI 细节 */
extern int*   find_nearest_enemy(void* out, float* refpos);          /* 0x425240 */
extern int    is_enemy_alive(int handle);                            /* 0x41a980 */
extern int    handle_to_enemy(int* phandle);                         /* 0x41b540 → 敌对象 ptr */
extern float  engine_atan2(float dy, float dx);                      /* 0x487aaa (CRT atan2 分派) */
extern void   math_add_normalize_angle(float* angle_field, float* target); /* TODO 地址(寻的里用) */
extern void   cartesian_from_polar(void* out_xy, float angle, float radius); /* 0x4476b0 */

/* ---- 可调参数 ---- */
#define BURST_FRAMES   24       /* 激光存活帧数(脉冲窗口);超过即熄灭 */
#define LOCK_RADIUS    240.0f   /* 锁敌半径(像素);喂给 find_nearest_enemy 的 XMM3 TODO 核实单位 */
#define CHARGE_RAMP    18.0f    /* idx2:每帧蓄力增量 */
#define CHARGE_CAP     512.0f   /* idx2:蓄力上限 */
#define BEAM_LEN_SCALE 0.5f     /* idx2:束长 = 蓄力 × 0.5 */

static inline float* F(int self, int off) { return (float*)(self + off); }

uint32_t __fastcall tick_tracking_burst_laser(int self)
{
    /* (0) 爆发寿命:活够 BURST_FRAMES 帧就熄灭(走 idx2 的 +0x8c==2 收尾路径)。
     *     fire_rate 会按节奏重发新束 → 形成脉冲。*/
    if (*(int*)(self + SLOT_LIFETIME) > BURST_FRAMES) {
        *(int*)(self + SLOT_STATE) = 2;   /* 让 idx2 的熄灭逻辑接手(关束/清 +0xb0/SFX) */
        /* 注:若发现束不消失,这里可能要主动清 SLOT_POOLLINK 链对象的 active 位(见 idx2 收尾段) */
        return 0;
    }
    if (*(int*)(self + SLOT_STATE) == 2) return 0;   /* 已结束 */

    /* (1) 追踪:取/续锁最近敌人,用 atan2 把移动角 +0x64 瞄向它(照搬 idx1 idx0x445ee0)。
     *     —— 这是相对 idx2 的唯一"方向源"改动:idx2 原本按 .sht 角/聚焦竖直,这里改成瞄敌。*/
    {
        int* tgt = (int*)(self + SLOT_TARGET);
        if (ENEMY_MANAGER == 0) {
            *tgt = 0;
        } else if (*tgt == 0) {
            float ref[2] = { *F(self, SLOT_X), *F(self, SLOT_Y) };
            /* TODO: 半径 LOCK_RADIUS 经 XMM3 传入(寻的用一个常量半径) */
            int* h = find_nearest_enemy(/*out*/ ref /*占位*/, ref);
            *tgt = (h ? *h : 0);
        }
        if (*tgt != 0) {
            if (!is_enemy_alive(*tgt)) {
                *tgt = 0;
            } else {
                int enemy = handle_to_enemy(tgt);
                if ((*(uint32_t*)(enemy + ENEMY_FLAGS) & 0xc000021) == 0) {
                    float dx = *(float*)(enemy + ENEMY_X) - *F(self, SLOT_X);
                    float dy = *(float*)(enemy + ENEMY_Y) - *F(self, SLOT_Y);
                    float target = engine_atan2(dy, dx);
                    /* 平滑拧向目标(idx1 用 math_add_normalize_angle 带速率限制;
                       激光可直接赋值以"硬瞄",或保留平滑——先用平滑更稳)*/
                    math_add_normalize_angle(F(self, SLOT_ANGLE), &target);
                }
            }
        }
    }

    /* (2) 激光蓄力/长度(照搬 idx2 0x446260)。*/
    if (*F(self, SLOT_CHARGE) < CHARGE_CAP)
        *F(self, SLOT_CHARGE) += CHARGE_RAMP;

    /* (3) 束体渲染:把蓄力归一化喂 anm vm,置拉伸标志(照搬 idx2)。
     *     TODO: 需 ANM_MANAGER 地址 + AnmManager__get_vm_with_id;此处给出语义,具体调用照 idx2。*/
    /*   vm = AnmManager__get_vm_with_id(ANM_MANAGER, *(self+SLOT_ANM_VM));
     *   vm[0x530] |= 8;  vm[0x70] = charge;
     *   vm[0x530] |= 0x10; vm[0x68] = charge * (1/512);  */

    /* (4) 束尾坐标(可选,用于命中几何/特效):endpoint = polar(angle, charge*0.5) + 起点。*/
    {
        float endpoint[2];
        cartesian_from_polar(endpoint, *F(self, SLOT_ANGLE), *F(self, SLOT_CHARGE) * BEAM_LEN_SCALE);
        /* 起点 = option 位置(idx2:PLAYER+0x6bc + (option-1)*0xe4);伤害沿 起点→endpoint。*/
        (void)endpoint;
    }

    /* (5) 伤害:★ 不用写。findings/08 已证:spawn 给每发弹建 +0xb0 伤害源(dmg = .sht dmg 字段),
     *     tick_bullets 每帧把 slot+0x48 位置拷进伤害源,敌人侧 enm_compute_damage_sources 自动判重叠扣血
     *     (封顶 = .sht max_dmg)。只要上面保持了 slot+0x48 位置(瞄敌飞过去 / 束体覆盖),伤害自动生效。*/

    return 0;
}

/* =============================================================================
 * init 配对(伤害免费后简化了 —— findings/08):
 *  - 简化起步版(无束体,只追踪+伤害):func_on_init = 3(0x4470e0,清 flag&0x3c + 清 +0x90 目标槽),
 *    这是 targeting 的正确前置(+0x90 须为 0 才会找新目标)。伤害靠 spawn 自带的点伤害源,自动生效。
 *  - 完整激光版(要束体渲染):func_on_init = 2(0x446200,清蓄力 +0xa0 + 接 +0xb0 + SFX),
 *    但 init2 不清 +0x90 → 本 tick 首帧需自清(SLOT_LIFETIME==0 时强制 *tgt=0)。
 *  - func_on_hit = 0:伤害不靠 hit 回调(走伤害源管线),不挂额外命中特效。
 *  - .sht 的 dmg 字段(shooter +0x02)= 实际伤害值;max_dmg(header +0x28)= 每帧对单敌封顶。
 * ========================================================================== */
