# sound_table.py — 把 exe 里的音效表（id → se_*.wav）按数据引用地址顺序恢复出来。
#
# 思路：所有 "se_*.wav" 字符串的数据引用（DAT_ 指针）集中在一张表里；按引用地址排序，
# 位置就是 play_sound(id) 的 id（表项步长恒定可当自检）。只读，不改库。
#   source tooling/env.sh && python tooling/ghidra/scripts/sound_table.py th18
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _driver import open_program, resolve  # noqa: E402

version = sys.argv[1] if len(sys.argv) > 1 else "th18"
r = resolve(version)
with open_program(r["proj_dir"], r["proj_name"], r["program"]) as prog:
    refs = []
    it = prog.getListing().getDefinedData(True)
    while it.hasNext():
        d = it.next()
        if not d.hasStringValue():
            continue
        s = str(d.getValue())
        if not (s.startswith("se_") and s.endswith(".wav")):
            continue
        for ref in prog.getReferenceManager().getReferencesTo(d.getAddress()):
            refs.append((ref.getFromAddress().getOffset(), s))
    refs.sort()
    if not refs:
        print("no refs"); sys.exit(1)
    base = refs[0][0]
    strides = sorted({b[0] - a[0] for a, b in zip(refs, refs[1:])})
    print(f"refs={len(refs)} base={base:#x} strides={[hex(x) for x in strides[:6]]}")
    stride = strides[0]
    for off, name in refs:
        idx = (off - base) // stride
        print(f"{idx:#04x} {off:#x} {name}")
