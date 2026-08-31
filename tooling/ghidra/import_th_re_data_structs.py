#!/usr/bin/env python3
"""Import exphp-share/th-re-data **type definitions** (structs/unions/enums/typedefs) into Ghidra.

The sibling `import_th_re_data.py` imports only funcs.json + statics.json *names*. ExpHP's struct
defs (`type-structs-own.json` + `type-structs-ext.json`, plus enums/aliases/unions) are NOT imported
by it (ExpHP has no Ghidra struct importer — see their README "I am not capable of importing ...").
This script fills that gap.

Design — **layout is always exact**: every struct member becomes either a properly-typed field
(when its declared type resolves cleanly AND the resolved size matches the on-offset gap) or a
`char NAME[size]` spacer that still carries the field *name*. Unknown/`__unknown` regions become
`char field_<off>[size]`. So even messy/partial ExpHP types import with correct byte layout + names.
Structs are topologically ordered by value-embedding (a `struct B` member of A is built before A;
pointer members never create an ordering edge — they emit as `void*`). `own` overrides `ext` on name
collision (own is the curated, fuller set).

Two ways to use it:

  (A) Emit a self-contained C header (pure Python, no Ghidra) and parse it into Ghidra however you
      like — e.g. feed each decl to the ghidra-re MCP `parse_type_declaration`, or Ghidra's CParser:
          python import_th_re_data_structs.py <DATA_DIR> --emit-c > th16_types.h
      `--check` validates every emitted struct's computed size == ExpHP's declared size.

  (B) Run as a PyGhidra script (Ghidra 12 = CPython + pyghidra; analyzeHeadless dropped Jython), which
      parses the generated header with Ghidra's CParser and adds the types to the program. Safe by
      default (skips type names that already exist; --overwrite replaces). Optionally applies the
      `type` field of statics.json to globals (--apply-statics, only onto undefined data):
          python import_th_re_data_structs.py <DATA_DIR> --project-dir DIR --project NAME \
                 --program /th16.exe [--overwrite] [--apply-statics] [--dry-run]

where <DATA_DIR> is a th-re-data game folder, e.g. ecl/vendor/th-re-data/data/th16.v1.00a/.
"""
import json, os, re, sys

# ---------------------------------------------------------------------------- parsing / resolving

_PRIM = {  # th-re-data primitive name -> (C spelling, size)
    "int8_t": ("char", 1), "uint8_t": ("unsigned char", 1), "char": ("char", 1),
    "int16_t": ("short", 2), "uint16_t": ("unsigned short", 2),
    "int32_t": ("int", 4), "uint32_t": ("unsigned int", 4),
    "int64_t": ("long long", 8), "uint64_t": ("unsigned long long", 8),
    "float": ("float", 4), "double": ("double", 8), "bool": ("char", 1), "void": ("void", 0),
}


def _san(n):
    return re.sub(r"[^A-Za-z0-9_]", "_", n or "")


def _parse_int(s):
    s = s.strip()
    return int(s, 16) if s.lower().startswith("0x") else int(s)


def load_types(data_dir):
    """Return (structs, aliases, enums, unions) with `own` overriding `ext` for structs."""
    def j(name):
        p = os.path.join(data_dir, name)
        return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
    structs = {}
    structs.update(j("type-structs-ext.json"))
    structs.update(j("type-structs-own.json"))   # own wins
    return structs, j("type-aliases.json"), j("type-enums.json"), j("type-unions.json")


def load_bitfields(data_dir):
    """type-bitfields.json: {名字: [[起始位, "u<宽>"|null, 字段名], ...]}，末项 name='__end'。

    th18 是目前唯一带这个文件的版本（th16/th17 都是空的），内容是 ANM VM 的标志位布局。
    """
    p = os.path.join(data_dir, "type-bitfields.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


def struct_comments(rows):
    """回收 ExpHP 拿零长度字段当注释写的那些槽（`struct zCOMMENT[0x0]`）。

    他在 README 里明说是为了「让注释在浏览代码时糊在脸上」。这些字段 size==0，
    会被 struct_members 跳过——布局因此是对的，但那句话就丢了。捡回来当结构体描述。
    """
    return [m for (_o, m, t) in rows if t == "struct zCOMMENT[0x0]" and m]


class Resolver:
    """Map a th-re-data type string to a C spelling + byte size, given a set of known type sizes."""

    def __init__(self, aliases, enums, struct_sizes):
        self.alias = dict(aliases)               # name -> {"def":..., "size":int}
        self.enums = set(enums)                  # enum names (treated as 4-byte int)
        self.struct_sizes = struct_sizes         # name -> size (filled as structs are sized)

    def size_of(self, ty):
        """Best-effort byte size of a type string, or None if unknown."""
        c, sz = self.resolve(ty)
        return sz

    def resolve(self, ty):
        """Return (c_spelling, size) or ('char', None) sentinel via (None, None) for 'give up'."""
        if ty is None:
            return (None, None)
        ty = ty.strip()
        # array:  ELEM[N]
        m = re.match(r"^(.*)\[\s*([0-9a-fA-Fx]+)\s*\]$", ty)
        if m:
            elem, n = m.group(1).strip(), _parse_int(m.group(2))
            ec, es = self.resolve(elem)
            if ec is None or es is None:
                return (None, None)
            return (f"{ec}[{n}]", es * n)
        # pointer:  BASE*  (any pointee -> void* ; pointers are always 4 bytes here, 32-bit)
        if ty.endswith("*"):
            return ("void *", 4)
        # struct / union / enum keyword
        for kw in ("struct ", "union ", "enum "):
            if ty.startswith(kw):
                name = ty[len(kw):].strip()
                if kw == "enum ":
                    return (f"_enum_{_san(name)}", 4) if name in self.enums else ("int", 4)
                if name in self.struct_sizes:
                    return (_san(name), self.struct_sizes[name])
                return (None, None)
        # primitive
        if ty in _PRIM:
            c, s = _PRIM[ty]
            return (c, s)
        # typedef/alias -> follow to a primitive of its size
        if ty in self.alias:
            return self.resolve(self.alias[ty]["def"])
        if ty in self.struct_sizes:                # bare struct name w/o keyword
            return (_san(ty), self.struct_sizes[ty])
        if ty in self.enums:
            return ("int", 4)
        return (None, None)


def struct_members(rows):
    """Yield (offset, name, ty, size) for real members; skip markers; size from next offset."""
    pts = [(int(o, 16), m, t) for (o, m, t) in rows]
    for i in range(len(pts) - 1):
        off, mem, ty = pts[i]
        nxt = pts[i + 1][0]
        if mem == "__end":
            break
        if mem == "__exact_size_known":
            continue
        size = nxt - off
        if size <= 0:
            continue
        name = _san(mem) if (mem and not mem.startswith("__unknown")) else f"field_{off:x}"
        yield off, name, ty, size


def declared_size(rows):
    return int(rows[-1][0], 16)


# ---------------------------------------------------------------------------- emit (topo + C)

def build(structs, aliases, enums, unions):
    """Return (ordered_struct_names, sizes, resolver). Unions folded in with structs for ordering."""
    all_structs = dict(structs)
    all_structs.update({k: [[o, m, t] for (m, t) in [(mm, tt) for (mm, tt) in v]]  # unions -> rows-like
                        for k, v in {}.items()})  # (unions handled separately; see emit)
    sizes = {name: declared_size(rows) for name, rows in structs.items()}
    res = Resolver(aliases, enums, sizes)

    # dependency edges: A -> B  when A has a *value* member of struct/union B (not via pointer)
    deps = {name: set() for name in structs}
    for name, rows in structs.items():
        for _off, _nm, ty, _sz in struct_members(rows):
            if ty is None or "*" in ty:
                continue
            base = re.sub(r"\[[0-9a-fA-Fx]+\]$", "", ty).strip()
            for kw in ("struct ", "union "):
                if base.startswith(kw):
                    base = base[len(kw):].strip()
            if base in structs:
                deps[name].add(base)

    # Kahn topological sort (leaves first). Cycles via value-embed are impossible in C ABI.
    order, ready = [], sorted(n for n, d in deps.items() if not d)
    remaining = {n: set(d) for n, d in deps.items()}
    seen = set(ready)
    while ready:
        n = ready.pop(0)
        order.append(n)
        for m in structs:
            if n in remaining[m]:
                remaining[m].discard(n)
                if not remaining[m] and m not in seen:
                    seen.add(m); ready.append(m); ready.sort()
    # append any left (shouldn't happen) so nothing is dropped
    for n in structs:
        if n not in order:
            order.append(n)
    return order, sizes, res


def emit_struct_c(name, rows, res):
    """Return (c_decl_string, computed_size). Layout-preserving."""
    lines = [f"struct {_san(name)} {{"]
    total = 0
    for off, fname, ty, size in struct_members(rows):
        c, sz = res.resolve(ty)
        if c is None or sz != size:                 # fall back to a named char spacer
            lines.append(f"  char {fname}[{size}];")
        elif "[" in c:                              # array type: "elem[N]"
            elem, n = c[:c.index("[")], c[c.index("[") + 1:-1]
            lines.append(f"  {elem} {fname}[{n}];")
        else:
            lines.append(f"  {c} {fname};")
        total += size
    lines.append("};")
    return "\n".join(lines), total


def emit_all(data_dir, want_enums=True, game_only=False):
    """game_only=True: emit only z* game structs; non-z embeds -> char[]; enums -> int. Yields a
    fully self-contained header (no Windows/d3d/enum deps) safe for Ghidra's CParser."""
    structs, aliases, enums, unions = load_types(data_dir)
    if game_only:
        structs = {n: r for n, r in structs.items() if n.startswith("z")}
        enums = {}                 # 'enum X' -> int (keeps header self-contained)
        want_enums = False
    order, sizes, res = build(structs, aliases, enums, unions)
    out, decls = [], []
    if want_enums:
        for ename, members in enums.items():
            body = ", ".join(f"{_san(nm)} = {val}" for nm, val in members)
            out.append(f"enum _enum_{_san(ename)} {{ {body} }};")
    for name in order:
        c, total = emit_struct_c(name, structs[name], res)
        decls.append((name, c, total, sizes[name]))
        out.append(c)
    return out, decls, res


# ---------------------------------------------------------------------------- self-check

def check(data_dir):
    _out, decls, _res = emit_all(data_dir)
    bad = [(n, total, want) for (n, _c, total, want) in decls if total != want]
    print(f"[check] {len(decls)} structs; layout-size OK for {len(decls) - len(bad)}")
    for n, total, want in bad:
        print(f"  MISMATCH {n}: emitted 0x{total:x} != declared 0x{want:x}")
    return not bad


# ---------------------------------------------------------------------------- Ghidra apply

def apply_ghidra(prog, data_dir, dry=False, overwrite=False, apply_statics=False, game_only=True):
    """Build the structs PROGRAMMATICALLY (StructureDataType + dtm.addDataType) — the canonical
    persist path. Ghidra's CParser does NOT reliably commit a multi-struct header to the program dtm,
    so we don't use it here."""
    from ghidra.program.model.data import (
        StructureDataType, ArrayDataType, PointerDataType, CategoryPath, DataTypeConflictHandler,
        CharDataType, UnsignedCharDataType, ShortDataType, UnsignedShortDataType, IntegerDataType,
        UnsignedIntegerDataType, LongLongDataType, UnsignedLongLongDataType, FloatDataType,
        DoubleDataType, VoidDataType)
    dtm = prog.getDataTypeManager()
    structs, aliases, enums, unions = load_types(data_dir)
    bitfields = load_bitfields(data_dir)
    if game_only:
        structs = {nm: r for nm, r in structs.items() if nm.startswith("z")}
        # 只扔 PE/Win32 那些常量表；zMainMenuId / zMenuInput 是货真价实的游戏枚举，要留。
        # （旧代码这里是 enums = {}，把两个游戏枚举一起扔了。）
        enums = {nm: v for nm, v in enums.items() if nm.startswith("z")}
    order, sizes, res = build(structs, aliases, enums, unions)
    cat, REPL = CategoryPath("/"), DataTypeConflictHandler.REPLACE_HANDLER
    PRIMDT = {"char": CharDataType.dataType, "unsigned char": UnsignedCharDataType.dataType,
              "short": ShortDataType.dataType, "unsigned short": UnsignedShortDataType.dataType,
              "int": IntegerDataType.dataType, "unsigned int": UnsignedIntegerDataType.dataType,
              "long long": LongLongDataType.dataType, "unsigned long long": UnsignedLongLongDataType.dataType,
              "float": FloatDataType.dataType, "double": DoubleDataType.dataType}
    VOIDP = PointerDataType(VoidDataType.dataType, 4)
    CHAR = CharDataType.dataType
    cache = {}                          # struct name -> resolved Ghidra DataType

    def to_dt(ty):
        """th-re-data type string -> Ghidra DataType, or None to fall back to char[]."""
        if ty is None:
            return None
        ty = ty.strip()
        mm = re.match(r"^(.*)\[\s*([0-9a-fA-Fx]+)\s*\]$", ty)
        if mm:
            base = to_dt(mm.group(1).strip())
            return ArrayDataType(base, _parse_int(mm.group(2)), base.getLength()) if base else None
        if ty.endswith("*"):
            return VOIDP
        for kw in ("struct ", "union ", "enum "):
            if ty.startswith(kw):
                nm = ty[len(kw):].strip()
                if kw == "enum ":
                    return PRIMDT["int"]
                return cache.get(_san(nm))
        if ty in _PRIM:
            return PRIMDT.get(_PRIM[ty][0])
        if ty in aliases:
            return to_dt(aliases[ty]["def"])
        return cache.get(_san(ty))

    n = dict(types=0, skipped=0, failed=0, enums=0, bitfields=0, statics=0)
    for name in order:
        try:
            s = StructureDataType(cat, _san(name), 0, dtm)
            for off, fname, ty, size in struct_members(structs[name]):
                dt = to_dt(ty)
                if dt is None or dt.getLength() != size:
                    dt = ArrayDataType(CHAR, size, 1)
                s.add(dt, size, fname, (ty or "")[:60])
            notes = struct_comments(structs[name])
            if notes:
                s.setDescription("[th-re-data] " + "; ".join(notes))
            # dry 时也进 cache：否则 to_dt 全返回 None，statics 的计数会假报 0
            cache[_san(name)] = dtm.addDataType(s, REPL) if not dry else s
            n["types"] += 1
        except Exception as e:
            n["failed"] += 1
    n["zEnemyData_present"] = 1 if dtm.getDataType(CategoryPath("/"), "zEnemyData") is not None else 0

    # ── 枚举 ──────────────────────────────────────────────────────────
    from ghidra.program.model.data import EnumDataType
    for ename, members in enums.items():
        try:
            e = EnumDataType(cat, _san(ename), 4, dtm)
            for mn, val in members:
                e.add(_san(mn), int(val))
            if not dry:
                dtm.addDataType(e, REPL)
            n["enums"] += 1
        except Exception:
            n["failed"] += 1

    # ── 位域 ──────────────────────────────────────────────────────────
    # 建成一个定宽结构体，位域挂在里面。**只建类型，不往任何字段上绑**——
    # zAnmBitfieldsLo 与 zAnmVmPrefix.flags_lo 的对应关系是按名字推的（ExpHP 没有任何
    # 字段声明用这两个类型），要在 AnmVm__run 上读位运算验过才算数。验过之后那条绑定
    # 属于「我们那层」，进 games/<版本>/symbols.json。
    for bname, rows in bitfields.items():
        try:
            end = next((int(b) for (b, _t, nm) in rows if nm == "__end"), 32)
            width = max(1, (end + 7) // 8)
            s = StructureDataType(cat, _san(bname), width, dtm)
            for (bit, ty, nm) in rows:
                if ty is None or nm == "__end":
                    continue                      # __unknown 空洞 / 结尾标记
                s.insertBitFieldAt(0, width, int(bit), UnsignedIntegerDataType.dataType,
                                   int(str(ty).lstrip("u")), _san(nm), None)
            if not dry:
                dtm.addDataType(s, REPL)
            n["bitfields"] += 1
        except Exception:
            n["failed"] += 1

    def to_dt_deep(ty):
        """给 statics 用的类型解析：指针**保留指向类型**。

        to_dt 把所有指针压成 void*，那是建结构体时的有意为之（免得 `struct A*` 在 A 之前
        出现就造出拓扑环）。但套到全局上就把最值钱的信息扔了——`PLAYER_PTR` 标成
        `zPlayer*` 而不是 `void*`，反编译才会给出 `PLAYER_PTR->field`，
        否则永远是 `*(float *)((int)PLAYER_PTR + 0x624)`。全局没有排序问题，可以深解。
        """
        if not ty:
            return None
        t = ty.strip()
        depth = 0
        while t.endswith("*"):
            t, depth = t[:-1].strip(), depth + 1
        if not depth:
            return to_dt(ty)
        for kw in ("struct ", "union ", "enum "):
            if t.startswith(kw):
                t = t[len(kw):].strip()
        base = cache.get(_san(t))
        if base is None:
            return to_dt(ty)                  # 认不出指向谁，退回 void*
        dt = base
        for _ in range(depth):
            dt = PointerDataType(dt, 4)
        return dt

    if apply_statics:
        from ghidra.program.model.data import DataUtilities
        from ghidra.program.model.data.DataUtilities import ClearDataMode
        af = prog.getAddressFactory().getDefaultAddressSpace().getAddress
        lst = prog.getListing()
        for r in json.load(open(os.path.join(data_dir, "statics.json"), encoding="utf-8")):
            ty = r.get("type")
            if not ty:
                continue
            dt = to_dt_deep(ty)         # 指针保留指向类型（见 to_dt_deep 的说明）
            a = af(int(r["addr"], 16))
            existing = lst.getDataAt(a)
            if dt is None or (existing is not None and existing.isDefined() and not overwrite):
                continue
            # ⚠️ 这里曾是个哑巴 bug：不论 overwrite 与否都用 CLEAR_ALL_UNDEFINED_CONFLICT_DATA，
            # 而它清不掉**已定义**的数据 —— 于是 --overwrite 对「自动分析已经猜了个类型」的地址
            # 完全无效，异常还被 except: pass 吞掉。th18 的 58 个 VTABLE_CARD_* 就这样一直卡在
            # 自动分析猜的 pointer[21] 上，套不成 zVTableCard。
            mode = (ClearDataMode.CLEAR_ALL_CONFLICT_DATA if overwrite
                    else ClearDataMode.CLEAR_ALL_UNDEFINED_CONFLICT_DATA)
            if not dry:
                try:
                    DataUtilities.createData(prog, a, dt, -1, mode)
                    n["statics"] += 1
                except Exception:
                    n["failed"] += 1          # 别再静默吞掉
            else:
                n["statics"] += 1
    return n


# ---------------------------------------------------------------------------- main

if __name__ == "__main__":
    if "--emit-c" in sys.argv:
        dd = next(a for a in sys.argv[1:] if not a.startswith("-"))
        out, _decls, _res = emit_all(dd, game_only="--game-only" in sys.argv)
        print("\n".join(out))
        sys.exit(0)
    if "--check" in sys.argv:
        dd = next(a for a in sys.argv[1:] if not a.startswith("-"))
        sys.exit(0 if check(dd) else 1)

    cp = globals().get("currentProgram")              # injected only in Ghidra script context
    if cp is not None:                                # mode A: inside Ghidra
        args = list(getScriptArgs())                  # noqa: F821
        dd = next((a for a in args if not a.startswith("-")), None) \
            or askDirectory("th-re-data dir", "Select").getPath()           # noqa: F821
        nn = apply_ghidra(cp, dd, "--dry-run" in args, "--overwrite" in args,
                          "--apply-statics" in args, game_only="--all-types" not in args)
        print("[th-re-data types] " + " ".join(f"{k}={v}" for k, v in nn.items()))
    else:                                             # mode B: standalone PyGhidra driver
        import argparse
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from _driver import add_project_args, open_program
        ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
        ap.add_argument("data_dir")
        add_project_args(ap)
        ap.add_argument("--overwrite", action="store_true")
        ap.add_argument("--apply-statics", action="store_true")
        ap.add_argument("--all-types", action="store_true", help="also import non-z Windows/d3d types")
        a = ap.parse_args()
        with open_program(a.project_dir, a.project, a.program,
                          tx="import th-re-data types", commit=not a.dry_run) as prog:
            nn = apply_ghidra(prog, a.data_dir, a.dry_run, a.overwrite, a.apply_statics,
                              game_only=not a.all_types)
        print("[th-re-data types] " + " ".join(f"{k}={v}" for k, v in nn.items()))
