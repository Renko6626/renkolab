# decompile_funcs.py — 只读打印若干函数的反编译（headless 版 decompile_function，MCP 断连/开不了库时用）。
#   source tooling/env.sh && "$JAVA_HOME/bin/python" tooling/ghidra/scripts/decompile_funcs.py th18 0x40e8c0 [0x40ebf0 ...]
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _driver import open_program, resolve  # noqa: E402

version, addrs = sys.argv[1], sys.argv[2:]
r = resolve(version)
with open_program(r["proj_dir"], r["proj_name"], r["program"]) as prog:
    from ghidra.app.decompiler import DecompInterface, DecompileOptions
    from ghidra.util.task import ConsoleTaskMonitor

    di = DecompInterface()
    di.setOptions(DecompileOptions())
    di.openProgram(prog)
    af = prog.getAddressFactory()
    fm = prog.getFunctionManager()
    for a in addrs:
        fn = fm.getFunctionContaining(af.getAddress(a))
        if not fn:
            print(f"=== {a} <no function>")
            continue
        print(f"=== {a} {fn.getName()} {fn.getSignature().getPrototypeString(True)} cc={fn.getCallingConventionName()}")
        res = di.decompileFunction(fn, 120, ConsoleTaskMonitor())
        if res.decompileCompleted():
            print(res.getDecompiledFunction().getC())
        else:
            print("!! decompile failed:", res.getErrorMessage())
