# scan_flags_readers.py — 全二进制兜底:证明 TH16 没有读 shooter flags(+0x38..0x57)的代码。
#
# 思路(完整性):shooter 结构只能经 sht_base 全局解析到
#   shooter = (idx&0xff)*0x58 + *(sht_base + 0x190 + set*4)
#   sht_base = *(player + 0x2c788)[主] / *(player + 0x2c78c)[副]
# 故"任何能解析出 shooter 指针的函数,其指令里必然出现立即数 0x2c788 或 0x2c78c"。
# 本脚本扫全程序所有指令:
#   (1) 枚举引用这两个立即数的全部函数 = 唯一的 shooter-指针生产者集合(branch a 完整集);
#   (2) 在这些函数里找任何 [reg+disp] 且 disp ∈ [0x38,0x57] 的内存访问(疑似 flags 读);
#   (3) 独立交叉核:全程序里同时含立即数 0x58 与 400(0x190) 的函数(解析惯用法),应与 (1) 吻合。
# 只读、不改库。配 run.sh 跑:scripts/run.sh <th16.exe> scripts/scan_flags_readers.py
# @category SHT

GATE = (0x2c788, 0x2c78c)
FLAG_LO, FLAG_HI = 0x38, 0x57

prog = currentProgram                      # noqa: F821 (pyghidra 注入)
listing = prog.getListing()
fm = prog.getFunctionManager()


def entry(fn):
    return fn.getEntryPoint().toString() if fn is not None else "<none>"


def scalars_in_operand(ins, i):
    """返回 operand i 里的 (有无寄存器, [标量值...])."""
    has_reg = False
    vals = []
    for obj in ins.getOpObjects(i):
        cn = obj.getClass().getSimpleName()
        if cn == "Register":
            has_reg = True
        elif cn == "Scalar":
            vals.append(obj.getValue() & 0xFFFFFFFF)
    return has_reg, vals


gate_funcs = {}      # entry -> [name, set(gate immediates seen)]
flag_hits = []       # (func_entry, func_name, ins_addr, disp, mnemonic)
resolve_funcs = {}   # entry -> name  (含 0x58 且 含 400)
n_ins = 0

it = listing.getInstructions(True)
# 先全程序扫一遍:标记 gate 函数 + 候选 resolve 函数
per_func_scalars = {}  # entry -> set(scalars)  仅对出现过的函数累积,用于 (3)
while it.hasNext():
    ins = it.next()
    n_ins += 1
    fn = fm.getFunctionContaining(ins.getAddress())
    fe = entry(fn)
    nop = ins.getNumOperands()
    for i in range(nop):
        has_reg, vals = scalars_in_operand(ins, i)
        for v in vals:
            if v in GATE:
                rec = gate_funcs.setdefault(fe, [fn.getName() if fn else "<none>", set()])
                rec[1].add(v)
            # 交叉核用:累积每函数标量
            if fn is not None:
                per_func_scalars.setdefault(fe, set()).add(v)
        # flags 位移候选:同一 operand 内既有寄存器又有 disp∈[0x38,0x57] → [reg+disp] 内存访问
        if has_reg:
            for v in vals:
                if FLAG_LO <= v <= FLAG_HI:
                    flag_hits.append((fe, fn.getName() if fn else "<none>",
                                      ins.getAddress().toString(), v, ins.getMnemonicString()))

# (3) 同时含 0x58 与 400 的函数
for fe, sc in per_func_scalars.items():
    if 0x58 in sc and 400 in sc:
        # 取函数名
        nm = gate_funcs.get(fe, [None])[0]
        if nm is None:
            f = fm.getFunctionContaining(prog.getAddressFactory().getAddress(fe)) if fe != "<none>" else None
            nm = f.getName() if f else "<none>"
        resolve_funcs[fe] = nm

print("=" * 72)
print("[scan_flags_readers] program=%s  instructions=%d  functions=%d"
      % (prog.getName(), n_ins, fm.getFunctionCount()))
print("=" * 72)

print("\n--- (1) 引用 sht_base 立即数 0x2c788/0x2c78c 的全部函数 (= shooter 指针生产者) ---")
print("    共 %d 个:" % len(gate_funcs))
for fe in sorted(gate_funcs):
    nm, gates = gate_funcs[fe]
    gs = ",".join(hex(g) for g in sorted(gates))
    print("    %-10s  %-32s  gates={%s}" % (fe, nm, gs))

print("\n--- (2) 上述 gate 函数里 disp∈[0x38,0x57] 的 [reg+disp] 访问 (疑似 flags 读) ---")
gate_set = set(gate_funcs.keys())
hits_in_gate = [h for h in flag_hits if h[0] in gate_set]
if not hits_in_gate:
    print("    无。gate 函数中没有任何 [reg+disp] 落在 0x38..0x57。")
else:
    print("    %d 处(需人工判断 base 寄存器是否持 shooter 指针):" % len(hits_in_gate))
    for fe, nm, ia, disp, mn in hits_in_gate:
        print("    %-10s %-28s @%s  %-6s disp=%#x" % (fe, nm, ia, mn, disp))

print("\n--- (3) 交叉核:同时含立即数 0x58 与 400(0x190) 的函数 (解析惯用法) ---")
print("    共 %d 个:" % len(resolve_funcs))
for fe in sorted(resolve_funcs):
    intop = "  (∈gate)" if fe in gate_set else "  (NOT in gate!)"
    print("    %-10s  %-32s%s" % (fe, resolve_funcs[fe], intop))

# 全程序 flags-disp 总数(仅供参照,绝大多数是别的结构)
print("\n--- 参照:全程序 [reg+disp] 且 disp∈[0x38,0x57] 共 %d 处(多数属其它结构,非 shooter) ---"
      % len(flag_hits))

print("\n[VERDICT-INPUT] gate_funcs=%d  flags_in_gate=%d  resolve_xcheck=%d"
      % (len(gate_funcs), len(hits_in_gate), len(resolve_funcs)))
print("[DONE]")
