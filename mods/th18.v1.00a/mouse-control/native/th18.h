/*
 * th18.h —— TH18 v1.00a 的全部死绑量,集中一处。
 *
 * 换 exe build 这些全部作废。每一项的出处见 ../../mouse-control/TARGET.md。
 * check_constants.py 会把带 SIG_ 的那几项拿去和真 exe 对账。
 */

#ifndef TH18_H
#define TH18_H

#include <windows.h>

/* ---- 版本守卫签名(与 runtime-probe 同源) ---- */
#define RVA_SIG_A        0x5b170u   /* Player__sub_45b170  VA 0x45b170 */
#define RVA_SIG_B        0x5caa0u   /* Player__on_tick     VA 0x45caa0 */

/* ---- 全局 ---- */
#define RVA_PLAYER_PTR   0xcf410u   /* PLAYER_PTR : zPlayer*   VA 0x4cf410 */
#define RVA_INPUT_HELD   0xca428u   /* INPUT_HELD : uint32     VA 0x4ca428 */
#define RVA_SUPERVISOR   0xccdf0u   /* SUPERVISOR : zSupervisor VA 0x4ccdf0 */
#define OFF_SV_HWND      0x58u      /* zSupervisor.main_window : HWND */

/* ---- INPUT_HELD 位(engine/card/th18/04 §1,逐位有证据) ---- */
#define IN_SHOOT         0x001u
#define IN_BOMB          0x002u
#define IN_FOCUS         0x008u
#define IN_UP            0x010u
#define IN_DOWN          0x020u
#define IN_LEFT          0x040u
#define IN_RIGHT         0x080u
#define IN_DIR_MASK      (IN_UP | IN_DOWN | IN_LEFT | IN_RIGHT)
#define IN_CARD          0x400u    /* 用卡(C)。读的是上升沿 INPUT_PRESSED & 0x400 */

/* ---- zPlayer 内偏移 ---- */
#define OFF_POS_X        0x620u     /* float px(派生自亚像素) */
#define OFF_POS_Y        0x624u
#define OFF_SUB_X        0x62cu     /* int 1/128 px —— 权威副本 */
#define OFF_SUB_Y        0x630u
#define OFF_FOCUS        0x476ccu   /* int 低速位。v1 未用:它在我们的 hook 点之后
                                     * 才被写入,读到的是上一帧;改读 INPUT_HELD 的 IN_FOCUS。 */
#define OFF_FLAGS        0x4779cu   /* uint;(& 0x180)==0 才走正常八向移动分支 */
#define OFF_SPD_U_CARD   0x477b4u   /* int 非低速·直线 */
#define OFF_SPD_F_CARD   0x477b8u   /* int   低速·直线 */
#define OFF_SPD_U_DIAG   0x477bcu   /* int 非低速·斜向 */
#define OFF_SPD_F_DIAG   0x477c0u   /* int   低速·斜向 */
#define OFF_SPEED_MULT   0x477ecu   /* float 速度倍率 */

/* ---- 弹幕区几何 ----
 * 游戏区在 640x480 虚拟空间里是 {x:32, y:16, w:384, h:448}
 * (ExpHP anm/stages-of-rendering.md;自机/弹幕/道具都画在这个 640x480 的 surface 0 上,
 *  最后由一个 ANM 脚本整体缩放 1x/1.5x/2x 到 640x480 / 960x720 / 1280x960)
 * 游戏坐标:x 以游戏区水平中心为 0,y 以游戏区顶边为 0。 */
#define VIRT_W           640
#define VIRT_H           480
#define PLAYFIELD_CX     224        /* 32 + 384/2 */
#define PLAYFIELD_TOP    16
#define SUBPIXEL         128        /* 1 px = 128 亚像素 */

/* 钳位(th18 一手,0x45b170 末尾)——同时反过来佐证游戏区就是 384x448 */
#define CLAMP_X_ABS      0x5c00     /* ±184 px */
#define CLAMP_Y_MIN      0x1000     /*   32 px */
#define CLAMP_Y_MAX      0xd800     /*  432 px */

#endif /* TH18_H */
