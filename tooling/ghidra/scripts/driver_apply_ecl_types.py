#!/usr/bin/env python3
# Headless GhidraProject driver: 把 ECL 结构体 + 函数首参类型持久化进 MCP 在用的同一工程。
# 为什么需要 driver:MCP retype_decompiler_variable 改不了 __thiscall 的 auto-param "this"
# (call_sub/get_int_arg/_int_arg_given_value/get_float_arg_ptr);只有 Ghidra API
# (setCustomVariableStorage + getParameter(0).setDataType) 能改,且须经 GhidraProject + proj.save() 落盘。
# (memory: ghidra-mcp-save-broken / re-workflow-fanout-cost —— 机械活写脚本,不派 agent。)
#
# 运行前必须先 MCP close_database 释放 ghidra_projects/th16.exe 的锁!
# 用法(env 由调用方设好 GHIDRA_INSTALL_DIR / JAVA_HOME):
#   python driver_apply_ecl_types.py
import pyghidra
pyghidra.start()

from ghidra.base.project import GhidraProject
from ghidra.program.model.data import PointerDataType
from ghidra.program.model.symbol import SourceType
from ghidra.app.util.cparser.C import CParser

PROJ_DIR = "/data/sunyunbo/www/THTK-Studio-2/research/files/ghidra_projects"
PROJ_NAME = "th16.exe"
US = SourceType.USER_DEFINED

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
PARAM_TYPES = [
    (0x472030, "zEclRunContext"), (0x471DB0, "zEclRunContext"), (0x473C90, "zEclRunContext"),
    (0x473D40, "zEclRunContext"), (0x473E40, "zEclRunContext"), (0x473EF0, "zEclRunContext"),
    (0x473FE0, "zEclRunContext"), (0x474090, "zEclRunContext"), (0x474330, "zEclRunContext"),
    (0x4743A0, "zEclRunContext"), (0x4747D0, "zEclRunContext"),
    (0x474860, "zEclStack"), (0x474810, "zEclStack"), (0x474740, "zEclFileManager"),
]

proj = GhidraProject.openProject(PROJ_DIR, PROJ_NAME, False)
prog = proj.openProgram("/", "th16.exe", False)
dtm = prog.getDataTypeManager()
fm = prog.getFunctionManager()
af = prog.getAddressFactory()

def va(x): return af.getDefaultAddressSpace().getAddress(x)

tx = prog.startTransaction("driver: ECL structs + param types")
ns = npt = 0
fails = []
try:
    cp = CParser(dtm)
    for d in STRUCTS:
        try:
            cp.parse(d); ns += 1
        except Exception:
            pass  # already defined from prior MCP session
    for a, tyname in PARAM_TYPES:
        f = fm.getFunctionAt(va(a))
        dt = dtm.getDataType("/" + tyname)
        if f is None or dt is None or f.getParameterCount() < 1:
            fails.append((hex(a), tyname, "no func/type/param")); continue
        ptr = PointerDataType(dt)
        try:
            f.getParameter(0).setDataType(ptr, US); npt += 1
        except Exception:
            try:
                f.setCustomVariableStorage(True)
                f.getParameter(0).setDataType(ptr, US); npt += 1
            except Exception as e:
                fails.append((hex(a), tyname, str(e)[:80]))
finally:
    prog.endTransaction(tx, True)

proj.save(prog)
# verify: print param0 type of each
print("[driver] structs_parsed=%d param_types_set=%d fails=%d" % (ns, npt, len(fails)))
for a, tyname in PARAM_TYPES:
    f = fm.getFunctionAt(va(a))
    p0 = f.getParameter(0).getDataType().getName() if (f and f.getParameterCount() >= 1) else "?"
    print("  %s param0 = %s" % (hex(a), p0))
for x in fails:
    print("  FAIL", x)
proj.close()
print("[driver] saved + closed OK")
