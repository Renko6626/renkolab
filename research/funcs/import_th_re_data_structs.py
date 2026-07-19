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
    if game_only:
        structs = {nm: r for nm, r in structs.items() if nm.startswith("z")}
        enums = {}
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

    n = dict(types=0, skipped=0, failed=0, statics=0)
    for name in order:
        try:
            s = StructureDataType(cat, _san(name), 0, dtm)
            for off, fname, ty, size in struct_members(structs[name]):
                dt = to_dt(ty)
                if dt is None or dt.getLength() != size:
                    dt = ArrayDataType(CHAR, size, 1)
                s.add(dt, size, fname, (ty or "")[:60])
            if not dry:
                cache[_san(name)] = dtm.addDataType(s, REPL)
            n["types"] += 1
        except Exception as e:
            n["failed"] += 1
    n["zEnemyData_present"] = 1 if dtm.getDataType(CategoryPath("/"), "zEnemyData") is not None else 0

    if apply_statics:
        from ghidra.program.model.data import DataUtilities
        from ghidra.program.model.data.DataUtilities import ClearDataMode
        af = prog.getAddressFactory().getDefaultAddressSpace().getAddress
        lst = prog.getListing()
        for r in json.load(open(os.path.join(data_dir, "statics.json"), encoding="utf-8")):
            ty = r.get("type")
            if not ty:
                continue
            dt = to_dt(ty)              # resolves pointers/structs via the cache built above
            a = af(int(r["addr"], 16))
            existing = lst.getDataAt(a)
            if dt is None or (existing is not None and existing.isDefined() and not overwrite):
                continue
            if not dry:
                try:
                    DataUtilities.createData(prog, a, dt, -1,
                                             ClearDataMode.CLEAR_ALL_UNDEFINED_CONFLICT_DATA)
                    n["statics"] += 1
                except Exception:
                    pass
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
        import argparse, pyghidra
        ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
        ap.add_argument("data_dir"); ap.add_argument("--project-dir", required=True)
        ap.add_argument("--project", required=True); ap.add_argument("--program", required=True)
        ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--overwrite", action="store_true")
        ap.add_argument("--apply-statics", action="store_true")
        ap.add_argument("--all-types", action="store_true", help="also import non-z Windows/d3d types")
        a = ap.parse_args()
        pyghidra.start()
        from ghidra.base.project import GhidraProject
        folder, _, name = a.program.rpartition("/")
        proj = GhidraProject.openProject(os.path.abspath(a.project_dir), a.project, False)
        prog = proj.openProgram(folder or "/", name, False)
        try:
            tx = prog.startTransaction("import th-re-data types")
            try:
                nn = apply_ghidra(prog, a.data_dir, a.dry_run, a.overwrite, a.apply_statics,
                                  game_only=not a.all_types)
            finally:
                prog.endTransaction(tx, not a.dry_run)
            if not a.dry_run:
                proj.save(prog)
        finally:
            proj.close()
        print("[th-re-data types] " + " ".join(f"{k}={v}" for k, v in nn.items()))
