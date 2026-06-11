#!/usr/bin/env python3
# TH16 (th16.exe) gameplay PRNG — bit-exact reference model + period proof.
# Reversed first-hand from th16.exe (imagebase 0x400000):
#   - single-step:  FUN_00449720 @0x449782..0x4497a7  (also FUN_00458db0 for stream B)
#   - gameplay draw: FUN_00402be0 (two single-steps/call; float wrappers 0x402cb0/c70/cf0 call it)
#   - seed:          FUN_0043b520 (d88=d80=(u16)timeGetTime); replay restore 0x449030/0x447760
# State is a single 16-bit word. Two independent streams share the same algorithm:
#   Stream A = DAT_004a6d88 / counter DAT_004a6d8c  (GAMEPLAY, replay-critical)
#   Stream B = DAT_004a6d80 / counter DAT_004a6d84  (init/other)
# Only TH16. Constants (0x9630,0x6553,ROL2) may differ in other ZUN games — do not assume.
#
# Run:  python3 th16_prng_model.py   -> prints permutation/period proof + a sample sequence.

MASK = 0xFFFF
K1, K2 = 0x9630, 0x6553

def rol2(t):
    # ASM: AX=t; SHL ECX,2 ; SHR AX,0xE ; ADD AX,CX  ==  ROL16(t,2)
    return ((t << 2) | (t >> 14)) & MASK

def step_t(s):
    # the pre-rotation value: t = ((s ^ 0x9630) - 0x6553) & 0xFFFF
    return ((s ^ K1) - K2) & MASK

def step(s):
    # single-step state advance (what FUN_00449720 stores & emits as new state)
    return rol2(step_t(s))

def draw32(s):
    # one GAMEPLAY draw (FUN_00402be0): two steps; returns (value32, new_state).
    # value32 = (t1<<16)|t2 using the PRE-rotation values; state advances 2 steps.
    t1 = step_t(s);  r1 = rol2(t1)
    t2 = step_t(r1); r2 = rol2(t2)
    return ((t1 << 16) | t2), r2

def randf_signed(u32):  # FUN_00402cb0 -> [-1, 1)
    return (u32 & 0xFFFFFFFF) * (2.0 ** -31) - 1.0

def randf_unit(u32):    # FUN_00402c70 -> [0, 1)
    return (u32 & 0xFFFFFFFF) * (2.0 ** -32)

def rand_angle(u32):    # FUN_00402cf0 -> [-pi, pi)   (K = 0x494700 = 683565248.0)
    return (u32 & 0xFFFFFFFF) / 683565248.0 - 3.14159274

def _cycle_lengths(f):
    seen = bytearray(65536); out = []
    for s in range(65536):
        if seen[s]:
            continue
        L = 0; x = s
        while not seen[x]:
            seen[x] = 1; x = f(x); L += 1
        out.append(L)
    return out

if __name__ == "__main__":
    from collections import Counter
    assert len({step(s) for s in range(65536)}) == 65536, "step() must be a permutation"
    sc = Counter(_cycle_lengths(step))
    print("single-step cycle structure :", dict(sc), "(full period 65536, one cycle)")
    print("fixed points                :", [s for s in range(65536) if step(s) == s] or "none")
    dc = Counter(_cycle_lengths(lambda s: step(step(s))))
    print("per-draw (2-step) structure :", dict(dc), "-> gameplay period 32768 draws")
    s = 0x1234; seq = []
    for _ in range(6):
        v, s = draw32(s); seq.append(v)
    print("draw32() from seed 0x1234   :", [hex(v) for v in seq])
    print("randf_signed sample         :", [round(randf_signed(v), 5) for v in seq[:4]])
    print("NOTE: value32 high/low 16b are consecutive correlated outputs (16-bit real state).")
