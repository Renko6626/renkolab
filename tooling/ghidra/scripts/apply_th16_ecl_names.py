# 把 TH16 ECL VM 的【函数命名 + 运行时结构体 + 函数参数类型】应用到 th16.exe 的 Ghidra 工程(可复现固化)。
#
# 本会话状态(2026-06-10):函数名 + 7 个 ECL 结构体 + 9 个非 thiscall 函数的首参类型已经 MCP 套用并存盘;
# ★ 4 个 __thiscall 函数(call_sub/get_int_arg/_int_arg_given_value/get_float_arg_ptr)的首参 MCP 改不了
#   auto-param "this",须靠本脚本(Ghidra API setCustomVariableStorage+setDataType)经 GhidraProject driver 补。
# 方法学:此类机械确定性套用一律【写脚本】,勿派 agent(agent 留给需判断的命名;见 memory re-workflow-fanout-cost)。
#
# ★ 与 apply_th16_bullet/math/sht_names.py 不同:本脚本的**名字来源不是我们的反编译**,而是
#   **ExpHP `exphp-share/th-re-data`(data/th16.v1.00a/funcs.json)** —— 社区一手 RE 的 TH16 符号表
#   (仅名字 + 结构体偏移,无语义注释)。本仓库已对照验证(见 research/ecl/03-thredata-crosscheck.md):
#   我们独立反出的弹幕/数学/SHT 函数与 ExpHP 命名**绝大多数语义吻合**(连 step_ex_NN 的 EX 索引都对上)。
#   本脚本把 ExpHP 的 45 个 ECL 子系统函数名导进工程,作为后续反 ecl_run 等的导航底图。
#   名字里的 "::" 在 Ghidra 名中以 "__" 代替。注释标 [th-re-data] 来源 + 本仓库已确认者标注。
#
# 本会话已通过 ghidra-re MCP rename_function + set_comment + save_database 落盘(函数名跨会话可靠);
# 本脚本是【可复现】路径:对全新工程用 GhidraProject driver / analyzeHeadless 重放(见下)。
#
# 用法:
#   A) 持久工程:analyzeHeadless <绝对工程目录> th16 -import <abs>/th16.exe \
#         -scriptPath <abs>/scripts -postScript apply_th16_ecl_names.py
#   B) 临时验证:scripts/run.sh files/th16.exe scripts/apply_th16_ecl_names.py
#   ⚠️ pyghidra CLI / analyzeHeadless-postScript 不持久化数据符号改动(见 bullet 脚本注);
#      本脚本只改函数名(MCP 已落盘),无数据符号,故 MCP 路径即可持久。
#
# 仅 TH16(imagebase 0x400000)。
# @category ECL

from ghidra.program.model.symbol import SourceType
from ghidra.program.model.listing import CodeUnit
from ghidra.app.cmd.disassemble import DisassembleCommand
from ghidra.app.cmd.function import CreateFunctionCmd

US = SourceType.USER_DEFINED

# (addr, ghidra_name, plate_comment)  —— 名源自 th-re-data;注释为角色 + 来源 + 本仓库交叉确认
FUNCS = [
    # ---- VM 核心(运行时解释循环 / 调用 / 栈)----
    (0x472030, "EclRunContext__ecl_run",
     "[th-re-data] *** per-frame ECL opcode interpreter loop ***: reads zEclRunContext.cur_location(PC), "
     "time-gates, dispatches opcode. THE dispatcher. NOT decompiled by community -> our prime target."),
    (0x471DB0, "EclRunContext__call_sub",
     "[th-re-data] CALL mechanism (sub call, push stack frame). TH16 ins 11. internals UNVERIFIED."),
    (0x473BC0, "Enemy__ecl_run", "[th-re-data] per-enemy per-frame ECL entry (drives its zEclVm)."),
    (0x474860, "EclStack__ecl_return", "[th-re-data] RET: pop stack frame."),
    (0x474740, "EclFileManager__find_sub_by_name",
     "[th-re-data] resolve sub by name over zEclFileManager.subroutines (V2 named subs / dynamic linking)."),
    (0x4747D0, "EclRunContext__get_subroutine_ptr", "[th-re-data] get sub bytecode ptr."),
    (0x474890, "Enemy__load_sub_by_name", "[th-re-data]"),
    # ---- 本仓库一手反 ecl_run 得出的 helper(ExpHP 未命名;ecl/04-ecl-vm-interpreter.md)----
    (0x474430, "ecl_spawn_async",
     "[OURS, ecl/04] CALL_ASYNC impl (ins 15/16): new zEclRunContext linked onto vm+0x1200 async_list_head. ExpHP unnamed."),
    (0x474810, "ecl_stack_alloc",
     "[OURS, ecl/04] STACK_ALLOC impl (ins 40): allocate stack frame on zEclStack. ExpHP unnamed."),
    (0x4744E0, "ecl_lookup_async",
     "[ours+th-re-data] lookup async run-context by id over vm+0x1200 (=ExpHP Enemy::lookup_async). Used by ins 17/18/19/20."),
    # ---- 栈 / 参数 / 局部变量访问 ----
    (0x473C90, "EclRunContext__ecl_get_int_arg", "[th-re-data] read stack-local/arg (int) via zEclStack base_offset."),
    (0x473D40, "EclRunContext__ecl_get_float_arg", "[th-re-data] read stack-local/arg (float)."),
    (0x473E40, "EclRunContext__ecl_get_int_arg_given_value", "[th-re-data]"),
    (0x473EF0, "EclRunContext__ecl_get_float_arg_given_value", "[th-re-data]"),
    (0x473FE0, "EclRunContext__ecl_push_473fe0", "[th-re-data] push onto zEclStack."),
    (0x474090, "EclRunContext__ecl_pushf_474090", "[th-re-data]"),
    (0x474330, "EclRunContext__get_int_arg0_ptr", "[th-re-data]"),
    (0x4743A0, "EclRunContext__get_float_arg_ptr", "[th-re-data]"),
    (0x4251D0, "EnemyData__ecl_get_int_arg__trampoline", "[th-re-data]"),
    (0x4251F0, "EnemyData__ecl_get_int_arg_ptr__trampoline", "[th-re-data]"),
    (0x425200, "EnemyData__ecl_get_float_arg__trampoline", "[th-re-data]"),
    (0x425220, "EnemyData__ecl_get_float_arg_ptr__trampoline", "[th-re-data]"),
    # ---- 全局/特殊变量访问器(本仓库独立反出,命名与 ExpHP 一致 -> research/ecl/01)----
    (0x423810, "Enemy__ecl_get_int_global",
     "[th-re-data] read special/global var (int) by neg id. OUR RE (ecl/01): table @0x4921ac = "
     "{int,int_ptr,float,float_ptr} -> NAMES MATCH ExpHP exactly. ✅✅"),
    (0x423F80, "Enemy__ecl_get_int_global_ptr",
     "[th-re-data] lvalue of writable global int var. OUR RE: returns ctx+0x1498.. (I0-I3) ptrs. ✅✅"),
    (0x424110, "Enemy__ecl_get_float_global",
     "[th-re-data] read special/global var (float). OUR RE (ecl/01): switch on neg var-id; ~30 fields "
     "cross-validated vs Priw8 (RNG, player pos, EI0-3@enemy+0x1498, EF0-3@+0x14a8, difficulty). ✅✅"),
    (0x424C10, "Enemy__ecl_get_float_global_ptr", "[th-re-data] lvalue of writable global float var. OUR RE: matches. ✅✅"),
    # ---- 高位 opcode(>=300 游戏指令)-> 敌机/弹幕 handoff ----
    (0x41DCB0, "EnemyData__ecl_run_over_300",
     "[th-re-data] handler for ECL opcodes >=300 (enmCreate/move/anm/et* high-level instrs). = README S.A "
     "fire site FUN_0041dcb0; CONFIRMED by our RE (bullets/01 S.A) as a bullet_spawn_wrapper caller / "
     "ECL->danmaku handoff. dispatch is segmented: low sys-opcodes in ecl_run, >=300 here. ✅"),
    (0x41DCA0, "Enemy__ecl_run_over_300__trampoline", "[th-re-data] trampoline -> ecl_run_over_300."),
    (0x423050, "EnemyData__ecl_enm_create", "[th-re-data] enmCreate (ECL ins 300/304)."),
    (0x423260, "EnemyData__ecl_anm_set_sprite", "[th-re-data]"),
    (0x4233A0, "EnemyData__ecl_sub_anm_various_4233a0", "[th-re-data]"),
    (0x4319E0, "LaserManager__ecl_545_impl__cancels_all", "[th-re-data] ECL ins 545 -> laser cancel-all."),
    (0x42C240, "ecl_554_stage_logo", "[th-re-data] ECL ins 554 (stage logo)."),
    (0x417F00, "ecl_spell_417f00", "[th-re-data]"),
    (0x40C040, "ecl_callSTD_40c040", "[th-re-data] ECL -> STD call."),
    (0x402B70, "ecl_move_rand_402b70", "[th-re-data] move-instruction helper."),
    (0x406320, "ecl_move_rand_406320", "[th-re-data]"),
    (0x4033D0, "PosVel__ecl_sub_4033d0_math", "[th-re-data]"),
    (0x425870, "ecl_bezier_425870", "[th-re-data] bezier move helper."),
    (0x425F10, "ecl_anmRgb1Time", "[th-re-data] anmRgb1Time instr."),
    (0x426020, "ecl_anmScaleTime", "[th-re-data] anmScaleTime instr."),
    # ---- 杂项 leaf / unknown(ExpHP 未确定语义)----
    (0x41DA30, "ecl_unknown551_41da30", "[th-re-data] ECL ins 551 (unknown)."),
    (0x41DB70, "ecl_unknown571", "[th-re-data] ECL ins 571 (unknown)."),
    (0x40D400, "ecl_leaf_40d400_usedonce", "[th-re-data]"),
    (0x424E40, "ecl_leaf_424e40_usedtwice", "[th-re-data]"),
    (0x4260D0, "ecl_sub_4260d0_usedonce", "[th-re-data]"),
    # 0x4252d0 / 0x4253b0 (ecl_funcset_*) 在本工程 Ghidra 未识别为函数,略。
]

# ---- ECL 运行时结构体(布局来自 ExpHP th-re-data th16.v1.00a;偏移已逐字段核 ecl/02,04)----
# 依赖顺序声明;CParser 解进 DataTypeManager。本会话已先经 MCP parse_type_declaration 建好并存盘;
# 本脚本是【可复现】路径(全新工程用 GhidraProject driver 重放)。
STRUCTS = [
    "struct zEclLocation { int subroutine_index; int offset_from_first_instruction; };",
    "struct zEclStack { int data[0x400]; int stack_offset; int base_offset; };",
    "struct zEclSubroutinePtrs { char* name; void* bytecode; };",
    "struct zEclRawInstructionHeader { int time; unsigned short opcode; unsigned short total_size; "
    "unsigned short variable_mask; unsigned char rank_mask; unsigned char parameter_count; "
    "unsigned char num_stack_refs; unsigned char _pad[3]; };",
    "struct zEclFileManager { void* vtable_0; int file_count; int subroutine_count; "
    "void* file_data_pointers[0x20]; struct zEclSubroutinePtrs* subroutines; unsigned char _pad[0x1008]; };",
    "struct zEclVm { void* vtable; void* _next; void* _prev; unsigned char _ctx[0x11ec]; "
    "struct zEclFileManager* file_manager; void* enemy; void* async_list_head; unsigned char _pad[8]; };",
    "struct zEclRunContext { float time; struct zEclLocation cur_location; struct zEclStack stack; "
    "int async_id; struct zEclVm* vm; int __set_by_ins_20; unsigned char difficulty_mask; "
    "unsigned char _pad0[3]; unsigned char float_i[0x180]; struct zEclLocation float_i_locs[8]; "
    "int __set_by_ins_18_19; };",
]
# (函数地址, 首参结构体名)。本会话 MCP 已套 9 个非 thiscall;★ 标的 4 个是 __thiscall,
# MCP retype_decompiler_variable 改不了 auto-param "this",须本脚本(Ghidra API setDataType)补。
PARAM_TYPES = [
    (0x472030, "zEclRunContext"),   # ecl_run
    (0x471DB0, "zEclRunContext"),   # call_sub          ★ thiscall
    (0x473C90, "zEclRunContext"),   # ecl_get_int_arg   ★ thiscall
    (0x473D40, "zEclRunContext"),   # ecl_get_float_arg
    (0x473E40, "zEclRunContext"),   # _int_arg_given_value ★ thiscall
    (0x473EF0, "zEclRunContext"),   # _float_arg_given_value
    (0x473FE0, "zEclRunContext"),   # ecl_push
    (0x474090, "zEclRunContext"),   # ecl_pushf
    (0x474330, "zEclRunContext"),   # get_int_arg0_ptr
    (0x4743A0, "zEclRunContext"),   # get_float_arg_ptr ★ thiscall
    (0x4747D0, "zEclRunContext"),   # get_subroutine_ptr
    (0x474860, "zEclStack"),        # ecl_return (param = &ctx->stack)
    (0x474810, "zEclStack"),        # ecl_stack_alloc
    (0x474740, "zEclFileManager"),  # find_sub_by_name
]

prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()
listing = prog.getListing()
dtm = prog.getDataTypeManager()

def va(x):
    return af.getDefaultAddressSpace().getAddress(x)

def make_structs():
    from ghidra.app.util.cparser.C import CParser
    p = CParser(dtm)
    n = 0
    for decl in STRUCTS:
        try:
            p.parse(decl); n += 1
        except Exception as e:
            print("  [STRUCT] %s ... %s" % (decl[:40], e))
    return n

def find_dt(name):
    dt = dtm.getDataType("/" + name)
    return dt

def apply_param_types():
    from ghidra.program.model.data import PointerDataType
    from ghidra.program.model.symbol import SourceType as _ST
    ok = 0
    for a, tyname in PARAM_TYPES:
        f = fm.getFunctionAt(va(a))
        dt = find_dt(tyname)
        if f is None or dt is None or f.getParameterCount() < 1:
            print("  [PTYPE MISS] 0x%08x %s" % (a, tyname)); continue
        ptr = PointerDataType(dt)
        try:
            f.getParameter(0).setDataType(ptr, _ST.USER_DEFINED); ok += 1
        except Exception:
            # __thiscall auto-param: switch to custom storage then retry
            try:
                f.setCustomVariableStorage(True)
                f.getParameter(0).setDataType(ptr, _ST.USER_DEFINED); ok += 1
            except Exception as e:
                print("  [PTYPE FAIL] 0x%08x %s: %s" % (a, tyname, e))
    return ok

def name_func(a, name, comment):
    ad = va(a)
    f = fm.getFunctionAt(ad)
    if f is None:
        DisassembleCommand(ad, None, True).applyTo(prog)
        CreateFunctionCmd(ad).applyTo(prog)
        f = fm.getFunctionAt(ad)
    if f is None:
        print("  [MISS] no function at 0x%08x (%s)" % (a, name))
        return 0
    f.setName(name, US)
    if comment:
        listing.setComment(ad, CodeUnit.PLATE_COMMENT, comment)
    return 1

tx = prog.startTransaction("apply TH16 ECL names + types (th-re-data)")
nf = miss = ns = npt = 0
try:
    for a, name, comment in FUNCS:
        r = name_func(a, name, comment)
        nf += r
        if r == 0:
            miss += 1
    ns = make_structs()
    npt = apply_param_types()
finally:
    prog.endTransaction(tx, True)

print("[apply_th16_ecl_names] funcs=%d missing=%d structs=%d param_types=%d" % (nf, miss, ns, npt))
