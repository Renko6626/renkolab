# 把 SHT 逆向结论(函数名 + 证据注释 + 跳转表标签)应用到 TH16 (th16.exe) 的 Ghidra 工程。
# source of truth = research/sht/findings/03/04 + 审计(00-METHOD 纪律)。MCP 的 save 有事务 bug、
# run.sh 建的是临时工程都不能可靠落盘,故用本脚本作**版本化、可复现**的固化手段。
#
# 用法(二选一):
#   A) 持久工程(推荐,会自动保存):
#      analyzeHeadless <绝对工程目录> th16 -import <绝对路径>/th16.exe \
#          -scriptPath <绝对路径>/scripts -postScript apply_th16_sht_names.py
#      (工程目录必须绝对路径;首次 -import 会自动分析,数分钟)
#   B) 临时验证(不持久):scripts/run.sh files/th16.exe scripts/apply_th16_sht_names.py
#
# 仅 TH16。地址为镜像 VA(imagebase 0x400000)。每条名字旁的注释即证据摘要。
# @category SHT

from ghidra.program.model.symbol import SourceType
from ghidra.program.model.listing import CodeUnit
from ghidra.app.cmd.disassemble import DisassembleCommand
from ghidra.app.cmd.function import CreateFunctionCmd

US = SourceType.USER_DEFINED

# (VA, 函数名, plate 注释=证据链)  —— 仅放 CONFIRMED(audit) 项;atan2 为 🟡 待证
FUNCS = [
    (0x443790, "sht_parse_resolve_funcptrs",
     "[TH16] SHT parser. Per shooterset walks shooters stride 0x58; replaces +0x28/2c/30/34 "
     "with ptrs from tables 4919c0(init)/4919a0(tick)/4a6f04(draw)/491980(hit) indexed by field int. "
     "Term=first byte(fire_rate)<0. Evidence: decompile+struct_16.js+.sht parse. CONFIRMED(audit)."),
    (0x440FB0, "player_shot_init",
     "[TH16] Resolves main(+0x2c788)+sub(+0x2c78c) .sht via sht_parse_resolve_funcptrs; "
     "sets shot state/hitbox/tasks(0x443720/30). Caller: player ctor 0x441c60. CONFIRMED(audit)."),
    (0x441C60, "player_ctor",
     "[TH16] Player ctor: operator_new(0x2c828), stores DAT_004a6ef8, calls player_shot_init. CONFIRMED."),
    (0x442560, "player_update_perframe",
     "[TH16] Player per-frame update. State machine switch on player+0x165a8 (0=spawn,1=alive,2=death...). "
     "Reached via task entry 0x443720. CONFIRMED(audit)."),
    (0x441CF0, "player_input_move",
     "[TH16] Alive-state input+movement. Reads keys DAT_004a52c8 -> 9-way dir +0x2c780; move speed from SHT; "
     "updates pos +0x61c/+0x620; then calls playershot_tick_dispatch for slot groups +0x660(x4),+0x9f0(x8). CONFIRMED."),
    (0x442380, "playershot_tick_dispatch",
     "[TH16] Per-frame player-shot TICK dispatch. Iterates slots stride 0xe4; if active(+0x00) "
     "calls func_on_tick ptr at slot+0xdc. CONFIRMED(audit)."),
    (0x445D40, "playershot_hit_dispatch",
     "[TH16] func_on_hit dispatch (collision callback). this+0x88->slot(player+0x1110,stride 0xc0); "
     "packed idx slot+0xac; mask 0xf0000=main/sub sht(+0x2c788/+0x2c78c); call func_on_hit shooter+0x34. "
     "CONFIRMED(audit, offsets corrected)."),
    (0x445E20, "playershot_launch_shared",
     "[TH16] Shared shot launch finalizer. slot+0x8c=2, scale angle+0x60; triggers the shot's ANM object's "
     "ON-SWITCH handler via anm_on_switch_funcs(0x491b0c)[anmobj+0x5d0] (=ANM render-state switch, NOT a SHT "
     "effect table). NOT collision (refutes ExpHP guess sub_445e20__collide). CONFIRMED(audit + th-re-data)."),
    (0x425240, "find_nearest_enemy",
     "[TH16] find_nearest_enemy(out,&refpos). Walk enemy list DAT_004a6dc0+0x180; skip if enemy+0x526c "
     "& 0xc000021; min sqdist via enemy x/y=+0x1250/+0x1254; return handle enemy+0x5740 or 0. CONFIRMED(audit)."),
    (0x487AAA, "crt_atan2_likely",
     "[TH16] MSVC CRT intrinsic dispatch __cintrindisp2(x, tbl 0x494e50). Likely atan2 (inferred from "
     "homing 0x445ee0 caller), NOT proven from stub. 0x47e0e0=YELLOW verify before asserting."),
    (0x445EE0, "playershot_tick_homing_idx1",
     "[TH16] func_on_tick idx1 = HOMING. find_nearest_enemy + atan2-like(0x487aaa) steer angle+0x60 toward "
     "enemy; give up after frame>0x3b(59). Used by Reimu/Spring(pl00). decompile+.sht+wiki. CONFIRMED(audit)."),
    (0x446260, "playershot_tick_laser_idx2",
     "[TH16] func_on_tick idx2 = LASER. Option-positioned; charge+0xa0 ramps to DAT_4946c0; stretched beam "
     "endpoint via FUN_004476b0; NO enemy targeting. Used by Marisa/Winter(pl01). decompile+.sht+wiki. CONFIRMED(audit)."),
    (0x446E00, "playershot_tick_curve_idx3",
     "[TH16] func_on_tick idx3 = constant-curvature. Body: if(state+0x8c==1) angle+0x60 += const(DAT_4944d8). "
     "NOT used by retail pl0X.sht. CONFIRMED behavior; usage=none."),
]

# (VA, 标签) —— SHT func_* 跳转表(ExpHP 按结构偏移命名 SHT_FUNC_28/2c/34/30_TABLE,我们给语义)
LABELS = [
    (0x4919C0, "sht_func_init_table"),     # ExpHP SHT_FUNC_28_TABLE
    (0x4919A0, "sht_func_tick_table"),     # ExpHP SHT_FUNC_2c_TABLE
    (0x491980, "sht_func_hit_table"),      # ExpHP SHT_FUNC_34_TABLE
    (0x4A6F04, "sht_func_draw_table_UNUSED"),  # ExpHP SHT_SHOOTER_30_TABLE;draw 索引在所有 .sht 恒为 0(.data)
    # 0x491b0c 不是 SHT 表 —— 经 th-re-data + 反编译证实是 ANM VM 的 on-switch 回调表(归 ../anm/),已移除。
    (0x491B0C, "anm_on_switch_funcs"),     # ExpHP ANM_ON_SWITCH_FUNCS, void*[4]: [0]=null,[1]=0x407900,[2]=0x405f20,[3]=0x406920 (AnmVm::on_switch__N). CORRECTED 2026-06-09, was "effect_behavior_dispatch_table".
]

prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()
listing = prog.getListing()
symtab = prog.getSymbolTable()

def va(x):
    return af.getDefaultAddressSpace().getAddress(x)

tx = prog.startTransaction("apply TH16 SHT names")
ok_f = ok_c = ok_l = miss = 0
try:
    for a, name, comment in FUNCS:
        ad = va(a)
        f = fm.getFunctionAt(ad)
        if f is None:
            # 裸码(只被 func 指针表引用,自动分析未建函数)→ 先反汇编再建函数
            DisassembleCommand(ad, None, True).applyTo(prog)
            CreateFunctionCmd(ad).applyTo(prog)
            f = fm.getFunctionAt(ad)
        if f is None:
            print("  [MISS] cannot create function at 0x%08x (%s) — skip" % (a, name))
            miss += 1
            continue
        f.setName(name, US)
        ok_f += 1
        if comment:
            listing.setComment(ad, CodeUnit.PLATE_COMMENT, comment)
            ok_c += 1
    for a, lbl in LABELS:
        symtab.createLabel(va(a), lbl, US)
        ok_l += 1
finally:
    prog.endTransaction(tx, True)

print("[apply_th16_sht_names] renamed=%d  comments=%d  labels=%d  missing=%d" %
      (ok_f, ok_c, ok_l, miss))
