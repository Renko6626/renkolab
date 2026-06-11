#!/usr/bin/env python3
"""Import exphp-share/th-re-data labels (funcs.json + statics.json) into Ghidra.

Safe by default: only fills Ghidra defaults (FUN_/DAT_/no symbol/no comment); never clobbers
names you already set. --overwrite replaces them; --dry-run previews counts.

Run inside Ghidra (Script Manager or `analyzeHeadless -postScript <this> <DATA_DIR>`), or as a
standalone PyGhidra driver (Ghidra 12 dropped Jython, so headless = CPython + pyghidra):

    python import_th_re_data.py <DATA_DIR> --project-dir DIR --project NAME --program /prog

where DATA_DIR is a th-re-data game folder, e.g. data/th16.v1.00a/.  Names use `::` for the
class; this flattens to `__`.  NOTE: data-symbol edits only persist via the driver's proj.save()
(analyzeHeadless -postScript does not save them); function renames persist either way.
"""
import json, os, re

_PLACEHOLDER = re.compile(r'^(sub_|nullsub_?|j_|thunk_?|FID_|\?|loc_|unknown_?)', re.I)
def _keep(n, incl): return bool(n) and (incl or not _PLACEHOLDER.match(n))
def _san(n): return re.sub(r'[^A-Za-z0-9_]', '_', n.replace("::", "__"))  # Foo::bar -> Foo__bar


def apply(prog, data_dir, dry=False, overwrite=False, incl=False):
    from ghidra.program.model.symbol import SourceType
    from ghidra.program.model.listing import CodeUnit
    US, DEF = SourceType.USER_DEFINED, SourceType.DEFAULT
    addr = prog.getAddressFactory().getDefaultAddressSpace().getAddress
    fm, st, lst = prog.getFunctionManager(), prog.getSymbolTable(), prog.getListing()
    n = dict(applied=0, overwritten=0, skipped=0, missing=0, comments=0)

    def comment(a, ctype, text):
        if not text or (lst.getComment(ctype, a) is not None and not overwrite):
            return
        if not dry:
            lst.setComment(a, ctype, "[th-re-data] " + text)
        n["comments"] += 1

    funcs = os.path.join(data_dir, "funcs.json")
    if os.path.exists(funcs):
        for r in json.load(open(funcs, encoding="utf-8")):
            if not _keep(r.get("name"), incl):
                continue
            a = addr(int(r["addr"], 16)); f = fm.getFunctionAt(a)
            if f is None:
                n["missing"] += 1; continue
            sym = f.getSymbol(); named = sym is not None and sym.getSource() != DEF
            if named and not overwrite:
                n["skipped"] += 1
            else:
                if not dry:
                    f.setName(_san(r["name"]), US)
                n["overwritten" if named else "applied"] += 1
            comment(a, CodeUnit.PLATE_COMMENT, r.get("comment"))

    statics = os.path.join(data_dir, "statics.json")
    if os.path.exists(statics):
        for r in json.load(open(statics, encoding="utf-8")):
            if not _keep(r.get("name"), incl):
                continue
            a = addr(int(r["addr"], 16)); p = st.getPrimarySymbol(a)
            named = p is not None and not p.isDynamic() and p.getSource() != DEF
            if named and not overwrite:
                n["skipped"] += 1
            else:
                if not dry:
                    p.setName(_san(r["name"]), US) if named else st.createLabel(a, _san(r["name"]), US)
                n["overwritten" if named else "applied"] += 1
            comment(a, CodeUnit.EOL_COMMENT, r.get("comment"))
            # statics' "type" field is intentionally not applied (could clobber existing data layout).
    return n


def _summary(n, dry, overwrite):
    tag = ("[dry-run] " if dry else "") + ("[overwrite] " if overwrite else "[safe] ")
    print(tag + "applied=%(applied)d overwritten=%(overwritten)d skipped=%(skipped)d "
          "missing=%(missing)d comments=%(comments)d" % n)


if __name__ == "__main__":
    cp = globals().get("currentProgram")          # injected only in Ghidra script context
    if cp is not None:                            # mode A: inside Ghidra (tool owns tx + save)
        args = list(getScriptArgs())              # noqa: F821
        dry, ov, incl = "--dry-run" in args, "--overwrite" in args, "--include-placeholders" in args
        dd = next((a for a in args if not a.startswith("-")), None) \
            or askDirectory("th-re-data dir", "Select").getPath()   # noqa: F821
        _summary(apply(cp, dd, dry, ov, incl), dry, ov)
    else:                                         # mode B: standalone PyGhidra driver
        import argparse, pyghidra
        ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
        ap.add_argument("data_dir"); ap.add_argument("--project-dir", required=True)
        ap.add_argument("--project", required=True); ap.add_argument("--program", required=True)
        ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--overwrite", action="store_true")
        ap.add_argument("--include-placeholders", action="store_true")
        a = ap.parse_args()
        pyghidra.start()
        from ghidra.base.project import GhidraProject
        folder, _, name = a.program.rpartition("/")
        proj = GhidraProject.openProject(os.path.abspath(a.project_dir), a.project, False)
        prog = proj.openProgram(folder or "/", name, False)
        try:
            tx = prog.startTransaction("import th-re-data")
            try:
                n = apply(prog, a.data_dir, a.dry_run, a.overwrite, a.include_placeholders)
            finally:
                prog.endTransaction(tx, not a.dry_run)
            if not a.dry_run:
                proj.save(prog)                  # required for data-symbol changes to persist
        finally:
            proj.close()
        _summary(n, a.dry_run, a.overwrite)
