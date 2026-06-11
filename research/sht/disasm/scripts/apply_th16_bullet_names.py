# 把 TH16 敌弹(弹幕)引擎逆向结论(函数名 + 数据符号名 + 证据注释)应用到 th16.exe 的 Ghidra 工程。
# source of truth = research/bullets/01-core-engine.md(过程报告)。与 apply_th16_sht_names.py /
# apply_th16_math_names.py 分开:本脚本是敌弹/弹幕子系统。
#
# 本轮(2026-06-09)结论由 主控 inline 钉锚点 → Workflow 扇出(15 agent)→ 主控【逐函数一手复核】产出。
# 复核中实打实纠出一处错误:bullet_beh_add_displacement(0x4161f0)完成时清的是 c68 的 0x1|0x8 位
# (mask 0xfffffff6),不是它自己的 0x80000(auto-analysis/agent 误判已在注释里修正)。
# 函数名已经 MCP rename+save 落盘;本脚本是【可复现固化】+ 唯一能给数据符号(DAT_*)真改名的途径。
# ★ 整张 VM/handler 表已与 thcrap 社区 etEx 表(research/ecl/ECL-info.md)交叉验证:obj+0xc68 == etEx
# 效果位场,opcode 整数 == EX_ 旧位值,~28/28 语义吻合(连 unused 空位都对齐)。独立外部佐证 = 最强一档。
#
# 用法(二选一):
#   A) 持久工程(推荐):
#      analyzeHeadless <绝对工程目录> th16 -import <绝对路径>/th16.exe \
#          -scriptPath <绝对路径>/scripts -postScript apply_th16_bullet_names.py
#   B) 临时验证:scripts/run.sh files/th16.exe scripts/apply_th16_bullet_names.py
#
# ⚠️ 落盘坑(2026-06-09 实测):**pyghidra CLI 跑本脚本不会存盘**(事务只在内存,退出即丢);
#   Ghidra 12 无 Jython,analyzeHeadless -postScript *.py 也不行。要把改动持久化进 MCP 在用的工程
#   (files/ghidra_projects, 程序名 "th16.exe"),用 GhidraProject 显式存:先 MCP close_database 释放锁,
#   再跑一个 driver:`GhidraProject.openProject(path,"th16.exe",False).openProgram("/","th16.exe",False)`
#   → startTransaction → setName/createLabel → endTransaction → `proj.save(prog)` → close。
#   函数名本会话已经 MCP rename+save 落盘;数据符号(g_bullet_mgr 等 4 个)由上述 driver 落盘并复核存活。
#
# 仅 TH16(imagebase 0x400000)。每条名字旁注释 = 证据/可信度摘要。✅=主控指令级一手复核。
# @category SHT

from ghidra.program.model.symbol import SourceType
from ghidra.program.model.listing import CodeUnit
from ghidra.app.cmd.disassemble import DisassembleCommand
from ghidra.app.cmd.function import CreateFunctionCmd

US = SourceType.USER_DEFINED

# ---- ✅ CONFIRMED(主控逐函数一手复核 2026-06-09)函数 ----
FUNCS = [
    # 管理器 / tick / 池
    (0x412860, "bullet_mgr_tick",
     "[TH16] per-frame traversal of bullet pool DAT_004a6dac active list (head +0x70, node via obj+0x10, "
     "next +0x14). Per bullet -> bullet_tick or bullet_vs_player_collide; buckets live bullets into render "
     "layers (mgr+0x10+obj.0xc84*4); alive count +0x40. Invoked by scheduler thunk @0x412c50 (prio 0x1c). ✅"),
    (0x411E70, "bullet_tick",
     "[TH16] per-bullet per-frame: anim timer -> behavior bitfield dispatch (obj+0xc68 bits -> bullet_beh_* "
     "handlers) -> position integrate (+0xc20 += g_frame_dt*+0xc2c) -> bullet_vs_player_collide -> offscreen "
     "cull (bullet_pool_free). ✅"),
    (0x412CB0, "bullet_pool_spawn",
     "[TH16] pop free list DAT_004a6dac+0x60; fill slot from FIRE DESCRIPTOR param_1: [0]=type,[1]=subtype,"
     "[2..4]=pos,[5]=baseAngle,[6]=spreadStep,[7]=speed,[8]=speed2,[9]=radialOff,[0xd9]=count,[0xda]=spreadMode"
     "(0..0xc),[0xdb]=init c68,[0xdd]=sfx(->+0xc80),[0xde]=init PC(->+0xc60),[10..]=0xc6 dwords bytecode "
     "(->obj+0xc88). Spread geometry uses prng_randf_signed/unit. Prepend to active list +0x70. CANCELS "
     "(bullet_pool_free) if spawned inside player hitbox (dist^2 < mgr+0x44). Then runs bullet_vm_exec once. ✅"),
    (0x412670, "bullet_pool_free",
     "[TH16] return slot to free list head DAT_004a6dac+0x60 (prev/next +4/+8), unlink from active list "
     "(+0x14/+0x18), state +0xc72=0, reset interpolator sentinels (0xfff0bdc1/0xffffffff blocks). ✅"),
    (0x411880, "bullet_mgr_ctor",
     "[TH16] bullet pool manager ctor: two _eh_vector_constructor_iterator_ arrays at +0x9c and +0x9ffe94, "
     "stride 0x1478, count 0x7d1 (2001 slots each); manager size 0x1403b28; sets DAT_004a6dac = this. ✅"),

    # VM + 碰撞
    (0x413860, "bullet_vm_exec",
     "[TH16] per-bullet motion bytecode VM. Program obj+0xc88 (stride 0x2c), PC obj+0xc60, opcode = instr "
     "word [8] (denormal-float bit-pattern == integer; 1.4013e-45==1 etc). For behavior opcodes the opcode "
     "int == the obj+0xc68 bit it enables. while(PC<0x12). Opcode table: bullets/01-core-engine.md S3. "
     "✅ (decode method + structure first-hand; a few helper uses single-source -> see doc)."),
    (0x4124B0, "bullet_vs_player_collide",
     "[TH16] coord +0xc20, radius +0xc40. Selects player_collide_rect (obj+0x20 bit0x40) / player_collide_"
     "circle. ret 1=hit (->obj+0xc72=3 dying + hit effect via FUN_0040e5c0), 2=graze (FUN_00444cf0 +0x20|4), "
     "0=miss. Player damage occurs INSIDE the collide fns. ✅"),
    (0x4438C0, "player_collide_rect",
     "[TH16] bullet AABB (coord+0xc20 +/- radius+0xc40 *0.5) vs player rect DAT_004a6ef8+0x2c730..+0x2c740. "
     "Overlap & player not invincible (+0x1663c<1) & state(+0x165a8) not 2/3/4 -> player_on_death. "
     "ret 1=hit / 2=graze(margin band) / 0=miss. ✅"),
    (0x4439E0, "player_collide_circle",
     "[TH16] dist^2(player +0x610/+0x614 -> bullet coord) vs (playerHitbox + bulletRadius)^2; "
     "playerHitbox = *(player+0x2c788)+4 (parsed SHT), bulletRadius via XMM2 (=obj+0xc40). near (dist^2<r^2) "
     "-> ret 1 + player_on_death (if not invincible +0x1663c); far -> ret 2 graze ring / 0 miss. ✅"),
    (0x443F10, "player_on_death",
     "[TH16] player hit/death: sets player state DAT_004a6ef8+0x165a8 = 4, spawns explosion effect, sprite "
     "anim. Called from player_collide_rect/circle on non-invincible contact. ✅ (call-context + state write)."),

    # 极坐标速度原语
    (0x417510, "vec2_from_polar",
     "[TH16] out[0]=cos(angle)*speed; out[1]=sin(angle)*speed (x87 fcos/fsin inline). thiscall(this=out, "
     "param_1=angle, param_2=speed). Used everywhere to (re)build velocity (+0xc2c/c30) from obj+0xc3c(angle) "
     "& obj+0xc38(speed). Resolves +0xc38=speed/+0xc3c=angle first-hand. ✅"),

    # 行为 handler(obj+0xc68 位场,每帧;到时限自清该位 —— 唯 add_displacement 例外)
    (0x414EC0, "bullet_beh_speed_boost",
     "[TH16] c68 bit 0x1. For <=16 frames overwrite velocity with effective speed = base(+0xc38) + "
     "(5.0 - acc*0.3125) projected along +0xc3c; counter +0xfa4>0x10 -> toggle bit 0x1 off. ✅"),
    (0x414FB0, "bullet_beh_accel_vec",
     "[TH16] c68 bit 0x4. Each frame velocity(+0xc2c/30/34) += accel(+0x1010/14/18)*dt; speed(+0xc38) += "
     "+0xffc*dt; if |vx|or|vy|>thr re-derive angle(+0xc3c)=atan2 & speed(+0xc38)=sqrt; counter -> +0x101c "
     "clears bit 0x4. ✅"),
    (0x4151E0, "bullet_beh_speed_ramp",
     "[TH16] c68 bit 0x200000. Per-frame: speed += +0x1284*dt; velocity += +0x1298/9c/a0*dt; re-derive "
     "angle via atan2 (no sqrt-speed rewrite); counter +0x1274 -> +0x12a4 clears bit 0x200000. ✅"),
    (0x4153E0, "bullet_beh_turn_accel",
     "[TH16] c68 bit 0x8. Each frame angle(+0xc3c) += turnRate(+0x1048)*dt (wrapped); speed(+0xc38) += "
     "accel(+0x1044)*dt; vec2_from_polar rebuilds velocity; counter +0x1034 -> +0x1064 clears bit 0x8. ✅"),
    (0x415570, "bullet_beh_speed_angle_transition",
     "[TH16] c68 bit 0x10. Phase A: speed ramp +0xc38-(+0x1080*spd)/+0x10ac. Phase B (counter +0x107c>=+0x10ac): "
     "SFX, angle mode switch (+0x10b8: set/wrap/normalize), speed=target +0x108c, rebuild velocity; "
     "+0x10b4>=+0x10b0 clears bit 0x10. ✅"),
    (0x415BB0, "bullet_beh_wall_bounce",
     "[TH16] c68 bit 0x40. Tests pos vs up-to-4 boundary planes (+0x1100 bits 1/2/4/8 -> sub-reflectors "
     "FUN_00415a10/415ae0/4158d0/415790: reflect angle + mirror pos), min speed +0x10d4, rebuild velocity; "
     "bounce count +0x10f4 -> +0x10f8 clears bit 0x40. ✅"),
    (0x415F90, "bullet_beh_move_to_point",
     "[TH16] c68 bit 0x20000. 3D path interpolator (FUN_00406e10 on +0x1394 block); per-frame displacement "
     "-> velocity(+0xc2c/30), angle = atan2; at end snaps pos to target +0x1208, speed +0x11f4, clears "
     "bit 0x20000. ✅"),
    (0x4161F0, "bullet_beh_add_displacement",
     "[TH16] c68 bit 0x80000. Each frame pos(+0xc20/24/28) += vec(+0x1250/54/58)*dt; limit +0x125c vs "
     "counter +0x122c. NOTE (corrects auto-analysis): on completion clears c68 bits 0x1|0x8 (mask 0xfffffff6) "
     "= disables speed_boost/turn_accel, NOT its own 0x80000 (unlike the 8 sibling handlers that self-clear). "
     "Own-bit termination path = TODO. ✅ mechanism / 🟡 termination."),
    (0x4162D0, "bullet_beh_offscreen",
     "[TH16] c68 bit 0x100 = EX_OFFSCREEN. Float countdown +0x12c0 (max_time); plus screen-corner "
     "angular-visibility test (rotate via FUN_004173a0, D3DXVec2Normalize, dot vs 4 view-rect corners from "
     "DAT_004c0f48). Toggles bit 0x100 off when counter expires or off-screen. ✅✅ (first-hand + community etEx)"),
    (0x415D80, "bullet_beh_wrap",
     "[TH16] c68 bit 0x1000 = EX_WRAP. Screen wrap-around: +0x118c bits 0-3 = walls (b); moves coord to "
     "opposite side using view-rect extent (DAT_004c0f48); count +0x1184 -> +0x1188 (a) toggles bit 0x1000. "
     "(Renamed from screen_clamp; community EX_WRAP params walls/count match.) ✅✅"),

    # spawn 包装
    (0x414DA0, "bullet_spawn_wrapper",
     "[TH16] builds a fire descriptor on stack and calls bullet_pool_spawn. Called by bullet_vm_exec "
     "(opcode 0x2000 child split) and by external fire sites FUN_0041dcb0/FUN_00431fe0/FUN_00438cb0 "
     "(ECL handoff candidates -> research/ecl/). ✅ (call graph)."),

    # ---- 子机制(graze / bounce / setsprite-interrupt / size-interp)----
    (0x444CF0, "player_graze",
     "[TH16] graze handler (called by bullet_vs_player_collide on ret 2). Bumps DAT_004a57c0 (HUD graze, "
     "cap 99999999) + DAT_004a57c4 (score-popup count); SFX 0x2a; spawns graze particle + score popup. "
     "Caller sets bullet +0x20 bit 0x4 = already-grazed guard. ✅"),
    (0x415A10, "bullet_bounce_up",    "[TH16] EX_BOUNCE wall bit 0x1 (UP): reflect angle + mirror pos_y at top. ✅"),
    (0x415AE0, "bullet_bounce_down",  "[TH16] EX_BOUNCE wall bit 0x2 (DOWN): reflect at bottom. ✅"),
    (0x415790, "bullet_bounce_left",  "[TH16] EX_BOUNCE wall bit 0x4 (LEFT, fires pos_x<-192): reflect at left. Matches community BOUNCE_L=4. ✅"),
    (0x4158D0, "bullet_bounce_right", "[TH16] EX_BOUNCE wall bit 0x8 (RIGHT, fires pos_x>=+192): reflect at right. Matches community BOUNCE_R=8. ✅"),
    (0x4173C0, "bullet_run_anm_interrupt",
     "[TH16] EX_SETSPRITE c&0x8000 path: sets bullet anm-vm interrupt slot +0x490 = 2. ✅"),
    (0x4171C0, "bullet_size_interp",
     "[TH16] EX_SIZE per-frame size interpolator (state block +0x13ec); mode 0x7/0x11 linear, 0x8 bezier; "
     "output -> +0x141c (size scalar). ✅"),

    # ---- 激光子系统(详见 research/bullets/03-lasers.md;EX_LASER = opcode 0x8000000)----
    (0x443AF0, "player_collide_laser_obb",
     "[TH16] LASER vs player = ROTATED OBB. Rotates (player+0x610/614 - laser_origin) into laser-local frame "
     "(crt_sinf/crt_cosf of -angle), tests box [0,half_len]x[-width,+width] inflated by player hitbox "
     "(+0x2c748/+0x2c74c). ret 1=hit->player_on_death (same invuln/state guards as bullets), 2=graze, 0=miss. ✅"),
    (0x430FC0, "laser_base_ctor",   "[TH16] LaserDataInf base ctor (clears, sets base vtable). ✅"),
    (0x431130, "laser_line_ctor",   "[TH16] LaserLineInf ctor (vtable 0x492424, size 0x1b20; EX_LASER a=0). ✅(RTTI)"),
    (0x431860, "laser_inf_ctor",    "[TH16] LaserInfiniteInf ctor (vtable 0x4923b8, size 0x1548; EX_LASER a=1). ✅(RTTI)"),
    (0x431900, "laser_curve_ctor",  "[TH16] LaserCurveInf ctor (vtable 0x4922e0). Spawn path != 0x8000000 (TODO). 🟡"),
    (0x4318C0, "laser_beam_ctor",   "[TH16] LaserBeamInf ctor (vtable 0x49234c). Spawn path != 0x8000000 (TODO). 🟡"),
    (0x4313B0, "laser_mgr_dtor",    "[TH16] CORRECTED 2026-06-09 (was laser_mgr_tick; th-re-data + decompile): LaserManager::DESTRUCTOR — frees +4/+8 sublists, FUN_0042cb00, then g_laser_mgr=0. NOT the per-frame tick (which is TBD). See ecl/03-thredata-crosscheck.md S3."),
    (0x432F40, "laser_line_frame_tick", "[TH16] LaserLineInf slot-4 master per-frame dispatch (update+collision+anim). ✅"),
    (0x4352F0, "laser_inf_frame_tick",  "[TH16] LaserInfiniteInf slot-4: 4-phase state machine 3 wait->4 expand->2 full->5 shrink->free; collision active only in 4/2. ✅"),
    (0x433510, "laser_line_collide_player", "[TH16] LaserLineInf slot-13 player collision wrapper -> player_collide_laser_obb. ✅"),
    (0x435610, "laser_inf_collide_player",  "[TH16] LaserInfiniteInf slot-13 player collision wrapper -> player_collide_laser_obb. ✅"),
    (0x431FE0, "laser_line_update", "[TH16] LaserLineInf slot-1 per-frame update. 🟡"),
    (0x436FD0, "laser_inf_update",  "[TH16] LaserInfiniteInf slot-1 per-frame update. 🟡"),
]

# ---- ✅ 数据符号(MCP 无法改名,只能靠本脚本) ----
GLOBALS = [
    (0x4A6DAC, "g_bullet_mgr",
     "[TH16] enemy-bullet pool manager pointer (operator_new(0x1403b28) in bullet_mgr_ctor). +0x60 free list, "
     "+0x70 active list, +0x40 alive count, +0x44 spawn-cancel radius^2, +0x10.. render-layer bucket heads, "
     "+0x9c & +0x9ffe94 the 2x2001 slot arrays (stride 0x1478). ⚠ NOT the enemy mgr DAT_004a6dc0. ✅"),
    (0x49F3E4, "g_bullet_type_table",
     "[TH16] per-bullet-type descriptor table, stride 0x114, indexed by obj+0x1474 (sprite/type idx). "
     "+0x00 collision radius (->obj+0xc40/c44), +0x04 render bucket (->obj+0xc84), +0x08 anim/hitbox class, "
     "+0x0c render-data ptr. Read by bullet_vm_exec opcode 0x200/0x20000000 and bullet_pool_spawn. ✅"),
    (0x49F2E0, "g_bullet_render_desc",
     "[TH16] base of the stride-0x114 render-registration descriptor passed to FUN_0045f160 at spawn "
     "(g_bullet_render_desc + type*0x114). ✅"),
    (0x4A6EE0, "g_laser_mgr",
     "[TH16] LASER manager (≠ g_bullet_mgr/DAT_004a6dac, ≠ enemy DAT_004a6dc0). +0x14 active list, +0x5e0 "
     "ring, +0x5e4 count (cap 512), +0x5e8 handle seq, +0x608 graze total. (per-frame tick fn = TBD; "
     "0x4313b0 is the destructor, corrected 2026-06-09.) ✅"),
]

prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()
listing = prog.getListing()
symtab = prog.getSymbolTable()

def va(x):
    return af.getDefaultAddressSpace().getAddress(x)

def name_func(a, name, comment):
    ad = va(a)
    f = fm.getFunctionAt(ad)
    if f is None:
        DisassembleCommand(ad, None, True).applyTo(prog)
        CreateFunctionCmd(ad).applyTo(prog)
        f = fm.getFunctionAt(ad)
    if f is None:
        print("  [MISS] no function at 0x%08x (%s)" % (a, name))
        return 0, 0
    f.setName(name, US)
    if comment:
        listing.setComment(ad, CodeUnit.PLATE_COMMENT, comment)
        return 1, 1
    return 1, 0

def rename_data(a, name, comment):
    ad = va(a)
    sym = symtab.getPrimarySymbol(ad)
    if sym is not None:
        sym.setName(name, US)
    else:
        symtab.createLabel(ad, name, US)
    if comment:
        listing.setComment(ad, CodeUnit.PLATE_COMMENT, comment)
    return 1

tx = prog.startTransaction("apply TH16 bullet names")
nf = nc = ngl = miss = 0
try:
    for a, name, comment in FUNCS:
        r, c = name_func(a, name, comment); nf += r; nc += c
        if r == 0:
            miss += 1
    for a, name, comment in GLOBALS:
        ngl += rename_data(a, name, comment)
finally:
    prog.endTransaction(tx, True)

print("[apply_th16_bullet_names] funcs=%d plate_comments=%d globals=%d missing=%d" %
      (nf, nc, ngl, miss))
