"""x86-32 常量定位器 —— 只回答一个问题：

  「.text 里某个 4 字节值出现在这里，它是**立即数**、**绝对地址**、
   还是**相对某寄存器的位移**？」

card-expand 的全部安全性都压在这个区分上：`0x4c5f8c` 既是卡表的尾界立即数
(`cmp eax, 0x4c5f8c`)，又是一个热全局的地址 (`mov eax, [0x4c5f8c]`)。
按值全局替换会把后者一起改掉。

**设计原则：不认识就报错，绝不猜。** 未覆盖的编码一律抛 UnknownEncoding，
由调用方决定是补规则还是放弃——静默跳过是不允许的。
"""

class UnknownEncoding(Exception):
    pass


# ---- 无 ModRM、常量即立即数 ----------------------------------------------
# opcode -> 助记符模板；常量在 +1，指令长 5
NO_MODRM_IMM = {
    0x05: "add eax, {c}",   0x0d: "or  eax, {c}",  0x15: "adc eax, {c}",
    0x1d: "sbb eax, {c}",   0x25: "and eax, {c}",  0x2d: "sub eax, {c}",
    0x35: "xor eax, {c}",   0x3d: "cmp eax, {c}",  0xa9: "test eax, {c}",
}
REG32 = ["eax", "ecx", "edx", "ebx", "esp", "ebp", "esi", "edi"]
for _i, _r in enumerate(REG32):
    NO_MODRM_IMM[0xb8 + _i] = "mov " + _r + ", {c}"

# ---- 无 ModRM、常量是绝对地址（moffs 形式）--------------------------------
NO_MODRM_MEM = {
    0xa0: "mov al, [{c}]",   0xa1: "mov eax, [{c}]",
    0xa2: "mov [{c}], al",   0xa3: "mov [{c}], eax",
}

# ---- 带 ModRM 的 opcode：(助记符, 尾随立即数字节数) -----------------------
# 立即数字节数 0 表示该指令没有尾随立即数（常量只可能来自 disp32）
MODRM_OPS = {
    0x00: ("add r/m8, r8", 0),   0x01: ("add r/m32, r32", 0),
    0x02: ("add r8, r/m8", 0),   0x03: ("add r32, r/m32", 0),
    0x08: ("or  r/m8, r8", 0),   0x09: ("or  r/m32, r32", 0),
    0x0b: ("or  r32, r/m32", 0),
    0x20: ("and r/m8, r8", 0),   0x21: ("and r/m32, r32", 0),
    0x23: ("and r32, r/m32", 0),
    0x28: ("sub r/m8, r8", 0),   0x29: ("sub r/m32, r32", 0),
    0x2b: ("sub r32, r/m32", 0),
    0x30: ("xor r/m8, r8", 0),   0x31: ("xor r/m32, r32", 0),
    0x33: ("xor r32, r/m32", 0),
    0x38: ("cmp r/m8, r8", 0),   0x39: ("cmp r/m32, r32", 0),
    0x3a: ("cmp r8, r/m8", 0),   0x3b: ("cmp r32, r/m32", 0),
    0x69: ("imul r32, r/m32, imm32", 4),
    0x6b: ("imul r32, r/m32, imm8", 1),
    0x80: ("<alu> r/m8, imm8", 1),
    0x81: ("<alu> r/m32, imm32", 4),
    0x83: ("<alu> r/m32, imm8", 1),
    0x84: ("test r/m8, r8", 0),  0x85: ("test r/m32, r32", 0),
    0x88: ("mov r/m8, r8", 0),   0x89: ("mov r/m32, r32", 0),
    0x8a: ("mov r8, r/m8", 0),   0x8b: ("mov r32, r/m32", 0),
    0x8d: ("lea r32, m", 0),
    0xc6: ("mov r/m8, imm8", 1),
    0xc7: ("mov r/m32, imm32", 4),
    0xd9: ("x87 d9", 0),  0xdb: ("x87 db", 0), 0xdd: ("x87 dd", 0),
    0xf6: ("grp3 r/m8", 1),      0xf7: ("grp3 r/m32", 0),
    0xff: ("grp5 r/m32", 0),
}
# 0f 前缀的双字节 opcode：一律无尾随立即数（我们只需要长度正确）
MODRM_0F_NOIMM = True


def _modrm(buf, i):
    """解出 (mod, reg, rm, 位移在 buf 里的偏移或 None, 位移字节数, 指令到位移末尾的长度)。"""
    m = buf[i]
    mod, reg, rm = m >> 6, (m >> 3) & 7, m & 7
    i += 1
    has_sib = (mod != 3 and rm == 4)
    sib_base = None
    if has_sib:
        sib_base = buf[i] & 7
        i += 1
    disp_off, disp_len = None, 0
    if mod == 1:
        disp_off, disp_len = i, 1
    elif mod == 2:
        disp_off, disp_len = i, 4
    elif mod == 0:
        if rm == 5:                       # [disp32] —— 绝对地址
            disp_off, disp_len = i, 4
        elif has_sib and sib_base == 5:   # [index*s + disp32] —— 也是绝对地址
            disp_off, disp_len = i, 4
    i += disp_len
    return mod, reg, rm, has_sib, sib_base, disp_off, disp_len, i


# 解释的可信度分级：越靠前的编码约束越强，冲突时优先采信。
#   abs  需要 opcode + modrm(mod=00,rm=101) 两个字节同时对上
#   imm/no-modrm 只需要 1 个字节对上 —— 最容易被巧合命中,排最后
TIER = {("abs", True): 0, ("disp", True): 1, ("imm", True): 2, ("imm", False): 3,
        ("abs", False): 3}


class Ambiguous(Exception):
    pass


def classify(buf, const_off, base_va, sect_off):
    """判断 buf[const_off:const_off+4] 这个 4 字节常量的角色。

    kind ∈ {"imm", "abs", "disp"}
      imm  —— 立即数（`cmp eax, K`），改它就是改常量 ✅
      abs  —— 绝对地址（`mov eax, [K]`），**不是常量,别碰** ⛔
      disp —— 相对某寄存器的位移（`lea eax, [eax+K]`）⚠️

    ⚠️ 回溯找指令起点天然有歧义：`83 3D <K> 00`（cmp dword [K], 0）
    的第 2 个字节 `3D` 自己就是 `cmp eax, imm32` 的 opcode，两种读法都
    「自洽」。**这是本工具唯一的软肋**，靠两道防线兜住：
      1. 分级择优（见 TIER）——约束强的编码优先；
      2. 上层 sites.py 的**形状校验**——分错了会表现为某个查表实例缺一条臂。
    同级出现两个解释就抛 Ambiguous，绝不静默二选一。
    """
    best, best_tier = None, 99
    for back in range(1, 13):
        start = const_off - back
        if start < 0:
            break
        try:
            end, fields, text, has_modrm = _decode(buf, start)
        except (UnknownEncoding, IndexError):
            continue
        if end != const_off + 4:
            continue
        for off, kind in fields:
            if off != const_off:
                continue
            tier = TIER[(kind, has_modrm)]
            cand = {"kind": kind, "va": base_va + (start - sect_off),
                    "len": end - start, "bytes": bytes(buf[start:end]),
                    "text": text, "tier": tier}
            if tier < best_tier:
                best, best_tier = cand, tier
            elif tier == best_tier and best is not None and cand["va"] != best["va"]:
                raise Ambiguous("0x%08x 处同级歧义：%s vs %s"
                                % (base_va + (const_off - sect_off),
                                   best["text"], cand["text"]))
    if best is None:
        raise UnknownEncoding("0x%08x 处的常量无法归类"
                              % (base_va + (const_off - sect_off)))
    return best


def _decode(buf, i):
    """解码 buf[i:]，返回 (结束偏移, [(4字节字段偏移, kind), …], 文本, 有无 ModRM)。

    只覆盖「可能携带 4 字节常量」的编码；碰到没覆盖的 opcode 抛
    UnknownEncoding，**绝不猜**。
    """
    start = i
    op = buf[i]

    if op in NO_MODRM_IMM:
        return (i + 5, [(i + 1, "imm")], NO_MODRM_IMM[op], False)
    if op in NO_MODRM_MEM:
        return (i + 5, [(i + 1, "abs")], NO_MODRM_MEM[op], False)

    if op == 0x0f:
        second = buf[i + 1]
        if 0x80 <= second <= 0x8f:
            return (i + 6, [], "jcc rel32", True)   # 跳转目标,不是常量
        i += 2
        mod, reg, rm, has_sib, sib_base, d_off, d_len, end = _modrm(buf, i)
        fields = []
        if d_len == 4:
            fields.append((d_off, "abs" if mod == 0 else "disp"))
        return (end, fields, "0f %02x /r" % second, True)

    if op not in MODRM_OPS:
        raise UnknownEncoding("未覆盖的 opcode %02x" % op)

    text, imm_len = MODRM_OPS[op]
    i += 1
    mod, reg, rm, has_sib, sib_base, d_off, d_len, end = _modrm(buf, i)
    imm_off = end
    end += imm_len

    fields = []
    if d_len == 4:
        fields.append((d_off, "abs" if mod == 0 else "disp"))
    if imm_len == 4:
        fields.append((imm_off, "imm"))
    return (end, fields, text, True)
