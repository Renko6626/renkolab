"""内联查表的**形状匹配器** —— card-expand 的权威站点来源。

不做「看见一个 4 字节值就猜它是什么」——那件事天然有歧义
（`83 3D <K> 00` 的第二个字节 `3D` 自己就是 `cmp eax, imm32` 的 opcode）。
改成整体匹配 MSVC 内联 `TableCardData__get` 后的固定骨架：

    mov  <p>, TABLE_BASE+f          ← LOOP_START
  L:cmp  [<p>], …                   ← 比较 entry->f
    jz   命中
  ┌ add  <p>, 0x34                  ← ★ 锚点
  └ inc  <i>
    cmp  <p>, TABLE_END+f           ← END
    jl   L
    mov  <p>, FALLBACK+g            ← FALLBACK
    jmp  之后
  命中:
    imul <p>, <i>, 0x34
    add  <p>, TABLE_BASE+g          ← HIT_ARM

锚点 `83 C0+r 34` + `40+r`（add r32,0x34 紧跟 inc r32）在整个 .text 里
**正好 25 处**，与 25 个内联点一一对应。匹配整段骨架 = 每次命中都自带
「四条臂配套」的保证，而这正是搬表唯一会**静默算错**的失败模式所在。
"""
import struct

REG32 = ["eax", "ecx", "edx", "ebx", "esp", "ebp", "esi", "edi"]
TABLE_BASE = 0x4c53c0


class ShapeError(Exception):
    pass


def _u32(b, i):
    return struct.unpack_from("<I", b, i)[0]


def _read(b, i, forms, what):
    """按给定编码表读一条指令。forms: [(前缀字节, 总长, 常量偏移, 模板)]。"""
    for pre, ln, coff, tmpl in forms:
        if b[i:i + len(pre)] == pre:
            reg = None
            if "{r}" in tmpl:
                reg = REG32[b[i + len(pre) - 1] & 7]
            return {"off": i, "len": ln, "const_at": coff,
                    "value": _u32(b, i + coff),
                    "text": tmpl.replace("{r}", reg or "?")}
    raise ShapeError("%s：0x%s 不是预期编码" % (what, b[i:i + 4].hex()))


def _forms_mov_imm():
    return [(bytes([0xb8 + r]), 5, 1, "mov {r}, K") for r in range(8)] + \
           [(b"\xc7\x45\x0c", 7, 3, "mov [ebp+0xc], K")]


def _forms_cmp_imm():
    return [(b"\x3d", 5, 1, "cmp eax, K")] + \
           [(bytes([0x81, 0xf8 + r]), 6, 2, "cmp {r}, K") for r in range(8)]


def _forms_add_imm():
    return [(b"\x05", 5, 1, "add eax, K")] + \
           [(bytes([0x81, 0xc0 + r]), 6, 2, "add {r}, K") for r in range(8)] + \
           [(bytes([0x8d, 0x80 + r]), 6, 2, "lea {r}, [{r}+K]") for r in range(8)]


def find_all(text, text_va):
    """扫出全部内联查表实例。返回 (实例列表, 锚点数)。"""
    anchors = [i for i in range(len(text) - 40)
               if text[i] == 0x83 and 0xc0 <= text[i + 1] <= 0xc7
               and text[i + 2] == 0x34 and 0x40 <= text[i + 3] <= 0x47]
    out = []
    for a in anchors:
        ptr_reg = text[a + 1] & 7
        idx_reg = text[a + 3] & 7
        i = a + 4
        end = _read(text, i, _forms_cmp_imm(), "END")
        i += end["len"]
        if text[i] != 0x7c:
            raise ShapeError("0x%06x：END 之后不是 jl" % (text_va + i))
        loop_head = i + 2 + struct.unpack_from("<b", text, i + 1)[0]
        i += 2
        # 循环走完 = 没找到 → 紧跟着就是 FALLBACK
        fb = _read(text, i, _forms_mov_imm(), "FALLBACK")

        # 命中臂用**循环头里的 jz 目标**定位，而不是靠「紧跟在 FALLBACK 之后」。
        # 编译器会把调用点的尾码复制进两条臂，中间夹多少指令都不一定。
        # 在循环体 [loop_head, anchor) 里找那条「命中就跳走」的 jz：
        # 判据是它的目标正好是 `imul r32, r/m32, 0x34`。
        # 不能只看循环头后几个字节——parse_ability_txt 的循环体是一整段
        # 内联 strcmp，jz 在 0x33 字节之后。
        hits = []
        for k in range(loop_head, a):
            if text[k] != 0x74:
                continue
            tgt = k + 2 + struct.unpack_from("<b", text, k + 1)[0]
            if 0 <= tgt < len(text) - 4 and text[tgt] == 0x6b and text[tgt + 2] == 0x34:
                hits.append(tgt)
        if len(hits) != 1:
            raise ShapeError("0x%06x：循环体里指向 imul 的 jz 有 %d 条(应为 1)"
                             % (text_va + loop_head, len(hits)))
        h = hits[0]
        hit = _read(text, h + 3, _forms_add_imm(), "HIT_ARM")

        # LOOP_START：从循环头往回找最近的 `mov <ptr_reg>, imm32`。
        # ⚠️ 找不到是**正常**的：编译器会把 `mov eax, TABLE_BASE+4` 提到分支
        # 之前，让两个循环共用一份（如 0x414412 同时供 0x414420 和 0x414494）。
        # 这里先留空，find_all 的第二遍再挂到最近的那一个上。
        start = None
        for back in range(2, 32):
            j = loop_head - back
            if j < 0:
                break
            if text[j] == 0xb8 + ptr_reg:
                try:
                    cand = _read(text, j, _forms_mov_imm(), "LOOP_START")
                except ShapeError:
                    continue
                if 0 <= cand["value"] - TABLE_BASE < 0x34:
                    start = cand
                break

        out.append({
            "anchor": text_va + a,
            "ptr_reg": REG32[ptr_reg], "idx_reg": REG32[idx_reg],
            "loop_head": text_va + loop_head,
            "parts": {k: dict(v, va=text_va + v["off"],
                              bytes=bytes(text[v["off"]:v["off"] + v["len"]]))
                      for k, v in (("end", end), ("fallback", fb), ("hit", hit))},
            "_start": (dict(start, va=text_va + start["off"],
                            bytes=bytes(text[start["off"]:start["off"] + start["len"]]))
                       if start else None),
        })

    # 第二遍：把没有本地 LOOP_START 的实例挂到**最近的前一个**上
    known = sorted((x["_start"]["va"], x["_start"]) for x in out if x["_start"])
    for x in out:
        if x["_start"] is None:
            prev = [v for va_, v in known if va_ < x["loop_head"]]
            if not prev:
                raise ShapeError("0x%06x：找不到可共用的 LOOP_START" % x["loop_head"])
            x["_start"], x["shared_start"] = prev[-1], True
        else:
            x["shared_start"] = False
        x["parts"]["start"] = x["_start"]
        del x["_start"]
    return out, len(anchors)


def find_walks(text, text_va):
    """找**表遍历**——它和查表是两种骨架，别混。

    查表按**地址**收尾（`cmp <p>, TABLE_END`），遍历按**计数**收尾：

        xor  <i>, <i>
        mov  <p>, TABLE_BASE+f     ← WALK_START（要跟着搬）
      L:… 用 [<p>] …
        inc  <i>
        add  <p>, 0x34
        cmp  <i>, COUNT            ← 计数上界（搬表时**不动**）
        jl   L

    锚点 = `add r32,0x34` 紧跟 `cmp r32,imm8` 再紧跟 `jl`。整个 .text 里
    正好 1 处：`CardCollection__mark_obtained_and_notify` 的全收集检查。

    ⚠️ 它逃过了查表的锚点（那个要求 `add` 之后紧跟 `inc`），
    最初就是被 sites.py 的完整性审计捞回来的——这条路径必须留着。
    """
    out = []
    for i in range(len(text) - 12):
        if not (text[i] == 0x83 and 0xc0 <= text[i + 1] <= 0xc7 and text[i + 2] == 0x34):
            continue
        if not (text[i + 3] == 0x83 and 0xf8 <= text[i + 4] <= 0xff and text[i + 6] == 0x7c):
            continue
        ptr_reg = text[i + 1] & 7
        count = text[i + 5]
        loop_head = i + 8 + struct.unpack_from("<b", text, i + 7)[0]
        start = None
        for back in range(2, 40):
            j = loop_head - back
            if j < 0:
                break
            if text[j] == 0xb8 + ptr_reg:
                cand = _read(text, j, _forms_mov_imm(), "WALK_START")
                if 0 <= cand["value"] - TABLE_BASE < 0x34:
                    start = cand
                break
        if start is None:
            continue                      # 步长 0x34 但不是我们这张表
        out.append({
            "anchor": text_va + i,
            "ptr_reg": REG32[ptr_reg],
            "count": count,
            "count_at": text_va + i + 5,
            "parts": {"start": dict(start, va=text_va + start["off"],
                                    bytes=bytes(text[start["off"]:
                                                     start["off"] + start["len"]]))},
        })
    return out
