#!/usr/bin/env python3
# Dump ALL functions (addr, name, size, xref-count) from the MCP-shared th16 Ghidra project
# to funcs/th16-funcs.json. Snapshot of "our current naming state" for the unexplored-function worklist.
#
# 运行前先 MCP close_database 释放 ghidra_projects/th16.exe 锁!(见 memory ghidra-mcp-save-broken)
# 用法:GHIDRA_INSTALL_DIR=... JAVA_HOME=... <conda ghidra>/bin/python funcs/dump_funcs.py
import json
import pyghidra
pyghidra.start()
from ghidra.base.project import GhidraProject

PROJ_DIR = "/data/sunyunbo/www/THTK-Studio-2/research/files/ghidra_projects"
OUT = "/data/sunyunbo/www/THTK-Studio-2/research/funcs/th16-funcs.json"

proj = GhidraProject.openProject(PROJ_DIR, "th16.exe", False)
prog = proj.openProgram("/", "th16.exe", False)
fm = prog.getFunctionManager()

out = []
for f in fm.getFunctions(True):
    ep = f.getEntryPoint()
    sym = f.getSymbol()
    xrefs = sym.getReferenceCount() if sym is not None else 0
    out.append({
        "addr": "0x%08x" % ep.getOffset(),
        "name": f.getName(),
        "size": f.getBody().getNumAddresses(),
        "xrefs": int(xrefs),
        "thunk": bool(f.isThunk()),
        "external": bool(f.isExternal()),
    })

json.dump(out, open(OUT, "w"), indent=0)
print("[dump_funcs] wrote %d functions -> %s" % (len(out), OUT))
proj.close()
