# find_imm_refs.py — 全 .text 扫指令里出现给定立即数 / 地址的地方（headless 版「谁引用了这个地址」）。
#   source tooling/env.sh && python tooling/ghidra/scripts/find_imm_refs.py th18 0x4c9b80 0x4c9b84 0x4b47a0
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _driver import open_program, resolve  # noqa: E402

version, targets = sys.argv[1], {int(x, 16) for x in sys.argv[2:]}
r = resolve(version)
with open_program(r["proj_dir"], r["proj_name"], r["program"]) as prog:
    fm = prog.getFunctionManager()
    for ins in prog.getListing().getInstructions(True):
        hit = None
        for i in range(ins.getNumOperands()):
            for obj in ins.getOpObjects(i):
                cn = obj.getClass().getSimpleName()
                v = None
                if cn == "Scalar":
                    v = obj.getValue() & 0xFFFFFFFF
                elif cn == "GenericAddress" or "Address" in cn:
                    v = obj.getOffset()
                if v in targets:
                    hit = v
        if hit is not None:
            fn = fm.getFunctionContaining(ins.getAddress())
            print(f"{ins.getAddress()}  {fn.getName() if fn else '?':<40} {ins}")
