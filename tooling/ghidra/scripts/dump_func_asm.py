# dump_func_asm.py — 只读打印一个函数的反汇编（headless 版 disassemble_function，MCP 断连时用）。
#   source tooling/env.sh && python tooling/ghidra/scripts/dump_func_asm.py th18 0x476c70 [0x476be0 ...]
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _driver import open_program, resolve  # noqa: E402

version, addrs = sys.argv[1], sys.argv[2:]
r = resolve(version)
with open_program(r["proj_dir"], r["proj_name"], r["program"]) as prog:
    af = prog.getAddressFactory()
    listing = prog.getListing()
    for a in addrs:
        addr = af.getAddress(a)
        fn = prog.getFunctionManager().getFunctionContaining(addr)
        print(f"=== {a} {fn.getName() if fn else '<no function>'}")
        body = fn.getBody() if fn else None
        it = listing.getInstructions(body, True) if body else listing.getInstructions(addr, True)
        n = 0
        for ins in it:
            print(f"{ins.getAddress()}  {ins}")
            n += 1
            if body is None and n > 80:
                break
