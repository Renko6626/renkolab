# 把 TH16 数学/CRT 模块逆向结论(函数名 + 常量名 + 证据注释)应用到 th16.exe 的 Ghidra 工程。
# source of truth = research/shared/th16-engine-math.md(过程报告)。与 apply_th16_sht_names.py 分开:
# 后者是 SHT/shoot-type,本脚本是跨主题的引擎数学子系统。MCP 的 save 有事务 bug、run.sh 建临时工程
# 都不能可靠落盘,故用本版本化脚本作可复现的固化手段。
#
# 用法(二选一):
#   A) 持久工程(推荐):
#      analyzeHeadless <绝对工程目录> th16 -import <绝对路径>/th16.exe \
#          -scriptPath <绝对路径>/scripts -postScript apply_th16_math_names.py
#   B) 临时验证:scripts/run.sh files/th16.exe scripts/apply_th16_math_names.py
#
# 仅 TH16(imagebase 0x400000)。每条名字旁注释 = 证据/可信度摘要。✅=指令级实证,🟡=未过对抗证伪。
# @category SHT

from ghidra.program.model.symbol import SourceType
from ghidra.program.model.listing import CodeUnit
from ghidra.app.cmd.disassemble import DisassembleCommand
from ghidra.app.cmd.function import CreateFunctionCmd

US = SourceType.USER_DEFINED

# ---- ✅ CONFIRMED(指令级 / 多源交叉)函数 ----
FUNCS = [
    (0x487AAA, "crt_atan2",
     "[TH16] CRT atan2 (_CIatan2) = atan2(ST1=dy, ST0=dx). 2-arg x87 intrinsic stub MOV EDX,0x494e50;JMP "
     "__cintrindisp2; x87 thunk path (FPATAN/FPTAN, not SSE2). Confirmed: float wrapper 0x4052a0 + 17 "
     "call-sites pass (dy,dx)->angle; zero-guard returns f_PI_2 (0x494534, atan2(0,0)->pi/2); two independent "
     "label-free agents ID'd atan2; adversarial pass could not refute. ✅."),
    (0x487ACA, "crt_fmod",
     "[TH16] CRT fmod(a,b) (_CIfmod). 2-arg x87 intrinsic stub MOV EDX,0x494940;JMP __cintrindisp2. "
     "x87 thunk at 0x487ad4 = FXCH; FPREM(0x487ad6, D9 F8); FNSTSW... (the fmod sequence; pow excluded by "
     "FPREM). Used in FUN_00417bc0 for sub-frame time remainder. ✅ (FPREM verified first-hand)."),
    (0x405510, "crt_sinf",
     "[TH16] sinf(x): CVTSS2SD -> kernel 0x4884c0(__libm_sse2_sin) -> CVTSD2SS. Resolved vs cos first-hand: "
     "rotation at FUN_0040e490 X'=X*(0x4054f0) - Y*(0x405510) = X*cos - Y*sin => 0x405510=sin. ✅."),
    (0x4054F0, "crt_cosf",
     "[TH16] cosf(x): CVTSS2SD -> kernel 0x488300(__libm_sse2_cos) -> CVTSD2SS. See 0x405510 for the "
     "rotation proof (0x4054f0 is the cos factor). ✅."),
    (0x4884C0, "libm_sse2_sin",
     "[TH16] __libm_sse2_sin kernel (double), called by crt_sinf 0x405510. ✅ (via rotation disambiguation)."),
    (0x488300, "libm_sse2_cos",
     "[TH16] __libm_sse2_cos kernel (double), called by crt_cosf 0x4054f0. ✅."),
    (0x488A00, "crt_floor",
     "[TH16] CRT floor(x) = round toward -inf (SSE2 bit-twiddle: PSRLQ exp extract, (bits>>sh)<<sh; "
     "NEG branch 0x488a98: CMPLTPD x<truncated -> ANDPD 1.0(0x494e00) -> SUBSD => subtract 1 when x negative "
     "non-integer = floor, NOT trunc). Callers: floor(elapsed/period) frame/score binning. "
     "✅ (adversarial pass corrected an initial 'trunc' misread; verified first-hand)."),
    (0x4052A0, "math_atan2f",
     "[TH16] float atan2(dy,dx): CVTSS2SD x2 -> push x87 -> CALL crt_atan2(0x487aaa) -> CVTPD2PS. "
     "All call-sites pass (src.y-dst.y, src.x-dst.x), result used as heading angle. ✅."),
    (0x402D90, "math_normalize_angle",
     "[TH16] normalize_angle(x)->(-pi,pi]; by value in/out XMM0. while(x>f_PI)x-=f_2PI; while(x<f_negPI)x+=f_2PI; "
     "iter cap 0x21. 34 callers (most-used pure normalizer). ✅ (instruction-level)."),
    (0x4052E0, "math_add_normalize_angle",
     "[TH16] *out = normalize_angle(*this + delta); delta passed in XMM2. Used by homing to advance heading "
     "by a steering increment then re-wrap. 2 callers. ✅."),
    (0x411410, "math_normalize_angle_field",
     "[TH16] *(this+0x1c) = normalize_angle(*(this+0x1c)); writes wrapped heading back to struct field +0x1c. "
     "8 callers; FUN_00410550 inlines the same wrap twice. ✅."),
    (0x430DF0, "math_set_velocity_polar",
     "[TH16] __thiscall set_velocity_from(angle,speed): FLD angle;FSINCOS;FMUL speed -> this[0]=cos*spd, "
     "this[1]=sin*spd. Writes only +0/+4. Inverse of the atan2 heading. ✅ (FSINCOS instruction-level)."),
    (0x4054D0, "math_set_velocity_polar_x87",
     "[TH16] same as math_set_velocity_polar but x87 fcos/fsin inlined: this[0]=cos(a)*r, this[1]=sin(a)*r. ✅."),
    (0x402BE0, "prng_gameplay_draw",
     "[TH16] gameplay PRNG draw (Stream A, state DAT_004a6d88, ctr+=2). Single step: t=((s^0x9630)-0x6553)"
     "&0xffff; s'=ROL16(t,2). This fn does TWO steps/call, returns 32-bit (t1<<16)|t2 (PRE-rotation words). "
     "16-bit state = FULL-PERIOD 65536 permutation (no fixed pts); gameplay period 32768 draws. "
     "Model: scripts/th16_prng_model.py. Optional CriticalSection 0x4c1048. ✅ instruction-level + period proven."),
    (0x449720, "prng_fill_stream_a",
     "[TH16] same recurrence as prng_core_step, fills 0x1ee outputs into buf at +0x14, advances DAT_004a6d88 "
     "and ctr DAT_004a6d8c. ✅ (algorithm); buffer use context 🟡."),
    (0x458DB0, "prng_init_warm_stream_b",
     "[TH16] one-time init (font enum + warms SECOND stream DAT_004a6d80 256x, same single-step algorithm; "
     "ctr DAT_004a6d84). Name takes the RNG facet. ✅ (algorithm)."),
    (0x43B520, "prng_seed_from_timeGetTime",
     "[TH16] startup init whose RNG side-effect seeds both streams: t=timeGetTime([0x48b24c]); "
     "DAT_004a6d88=DAT_004a6d80=(u16)t. Also sets DAT_004a5788=1.0f (frame dt). Registered as init callback "
     "by FUN_0043ba40. ✅ (the seeding); function also does unrelated startup work."),
    (0x402CB0, "prng_randf_signed",
     "[TH16] random float in [-1,1): raw=prng_core_step(&d88); u=(uint32)raw (fixup tbl 0x494850={0,2^32}); "
     "return u*2^-31(0x4943d4) - 1.0(0x4944d8). 45 callers (most-used). ✅ (constants read from PE)."),
    (0x402C70, "prng_randf_unit",
     "[TH16] random float in [0,1): u*2^-32(0x4943d0), no offset. 21 callers. ✅."),
    (0x402CF0, "prng_rand_angle",
     "[TH16] random angle in [-pi,pi): u/(2^31/pi)(0x494700) - pi(0x494588). 2 callers. ✅."),
    (0x402FF0, "motion_update_mode",
     "[TH16] per-frame motion updater, switch(*(obj+0x40)&0xf): set-vel-from-angle/position-integrate+wrap. "
     "Uses the angle/polar primitives. ✅ (behavior)."),
    (0x403110, "motion_update_mode_full",
     "[TH16] richer motion updater (3-component position; case3 = 2D rotation (x*c-y*s, x*s+y*c) via the "
     "sin/cos wrappers). ✅ (behavior)."),
]

# ---- 🟡 TENTATIVE(结构确证、细节布局未全解)----
FUNCS_TENTATIVE = [
    (0x449030, "prng_save_restore_replay_state",
     "[TH16] replay-RNG state save/restore. mode0: snapshot seed, DAT_004a6d80:=(u16)DAT_004a6d88; "
     "mode1: restore both streams from saved word + REP MOVSD 0x8a param block to 0x4a5790. "
     "Structure ✅; 0x294-record / 552-byte layout 🟡."),
    (0x447760, "prng_save_restore_replay_state_b",
     "[TH16] sibling of 0x449030 (same 3-case save/restore of DAT_004a6d88 into a 0x294 record). 🟡 layout."),
]

# ---- 数学常量重命名(值由 th16.exe PE 字节实测,见 shared/th16-engine-math.md §4)----
CONSTS = [
    (0x494588, "f_PI"),          # 3.14159274
    (0x4945B8, "f_2PI"),         # 6.28318548
    (0x494734, "f_negPI"),       # -3.14159274
    (0x494534, "f_PI_2"),        # 1.57079637
    (0x4944C0, "f_PI_4"),        # 0.785398185
    (0x494464, "f_PI_12"),       # 0.261799395 (15 deg)
    (0x4943E8, "f_inv512"),      # 0.001953125
    (0x4943F4, "f_inv128"),      # 0.0078125
    (0x494644, "f_128"),         # 128.0
    (0x4943D4, "f_rng_2pow_m31"),    # 2^-31  (randf_signed scale)
    (0x4943D0, "f_rng_2pow_m32"),    # 2^-32  (randf_unit scale)
    (0x494700, "f_rng_2pow31_div_pi"),  # ~2^31/pi (rand_angle scale)
    (0x4944D8, "f_one"),         # 1.0 (randf_signed bias)
    (0x494850, "d_rng_unsigned_fixup_tbl"),  # double[2] = {0.0, 2^32}
]

# ---- 引擎/RNG 状态全局变量(✅ 由反汇编 xref/写入点坐实)----
GLOBALS = [
    (0x4A6D88, "g_rng_state_a",      # u16 — Stream A live state (GAMEPLAY, replay-critical)
     "[TH16] 16-bit RNG state, Stream A (gameplay/replay). Stepped by prng_gameplay_draw(0x402be0) & "
     "prng_fill_stream_a(0x449720); seeded (u16)timeGetTime in prng_seed_from_timeGetTime(0x43b520); "
     "saved/restored on replay (0x449030/0x447760). Full-period 65536. ✅."),
    (0x4A6D8C, "g_rng_counter_a",    # u32 — draw counter for Stream A (state+4)
     "[TH16] Stream A draw counter (g_rng_state_a+4). INC per single-step; reset 0 at game/replay start; "
     "saved with replay (sync/desync tracking). ✅."),
    (0x4A6D80, "g_rng_state_b",      # u16 — Stream B live state
     "[TH16] 16-bit RNG state, Stream B. Same algorithm; stepped by 0x458db0 (warmed 256x at init). ✅."),
    (0x4A6D84, "g_rng_counter_b",    # u32 — draw counter for Stream B (state+4)
     "[TH16] Stream B draw counter (g_rng_state_b+4). ✅."),
    (0x4C1804, "g_rng_seed_timeGetTime",  # u32 — full timeGetTime() value captured at seeding
     "[TH16] full 32-bit timeGetTime() captured at seed (0x43b520 MOV [0x4c1804],EAX); low 16 bits become "
     "g_rng_state_a/b. ✅."),
    (0x4C1048, "g_rng_critsec",      # CRITICAL_SECTION guarding RNG when thread-safe path on
     "[TH16] CRITICAL_SECTION for thread-safe RNG (EnterCriticalSection arg in 0x402be0/0x449720). ✅."),
    (0x4C10B6, "g_rng_threadsafe_flag",  # byte — when set, RNG steps guard with g_rng_critsec
     "[TH16] when nonzero, RNG steppers wrap state update in g_rng_critsec. ✅."),
    (0x4C10B2, "g_rng_in_critsec_depth", # byte — INC/DEC around the critical section
     "[TH16] byte INC'd on EnterCriticalSection / DEC'd on Leave around RNG state update (lock-depth). ✅."),
    (0x4A5788, "g_frame_dt",         # float 1.0f — per-frame delta-time scale
     "[TH16] per-frame delta-time scale (=1.0f, set in 0x43b520). Multiplies velocity in motion integrators "
     "(0x402ff0/0x403110, math_set_velocity_polar callers). ✅."),
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

def rename_data(a, name):
    ad = va(a)
    sym = symtab.getPrimarySymbol(ad)
    if sym is not None:
        sym.setName(name, US)
    else:
        symtab.createLabel(ad, name, US)
    return 1

tx = prog.startTransaction("apply TH16 math names")
nf = nc = nt = ncc = ngl = miss = 0
try:
    for a, name, comment in FUNCS:
        r, c = name_func(a, name, comment); nf += r; nc += c
        if r == 0:
            miss += 1
    for a, name, comment in FUNCS_TENTATIVE:
        r, c = name_func(a, name, comment); nt += r
        if r == 0:
            miss += 1
    for a, name in CONSTS:
        ncc += rename_data(a, name)
    for a, name, comment in GLOBALS:
        rename_data(a, name)
        if comment:
            listing.setComment(va(a), CodeUnit.PLATE_COMMENT, comment)
        ngl += 1
finally:
    prog.endTransaction(tx, True)

print("[apply_th16_math_names] confirmed=%d tentative=%d plate_comments=%d consts=%d globals=%d missing=%d" %
      (nf, nt, nc, ncc, ngl, miss))
