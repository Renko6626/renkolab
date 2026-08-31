#!/usr/bin/env python3
"""Dump 一个 Ghidra 工程里的全部函数（addr / name / size / xref 数）到 JSON。

这是「我们当前命名状态」的快照，喂给 build_worklist.py 算出待挖清单。
被 bootstrap.py 调用，也可单独跑：

    P=/data/sunyunbo/miniconda3/envs/ghidra
    JAVA_HOME=$P GHIDRA_INSTALL_DIR=/data/sunyunbo/opt/ghidra_12.1.2_PUBLIC \
      $P/bin/python tooling/ghidra/dump_funcs.py \
        --project-dir "$(pwd)/local/th16.v1.00a/ghidra_projects" \
        --project th16.exe --program /th16.exe \
        --out local/th16.v1.00a/th16-funcs.json

⚠️ 运行前先让 MCP `close_database` 释放工程锁，否则会撞锁。
⚠️ 工程目录必须是绝对路径。
"""
import argparse, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _driver import open_program

ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
ap.add_argument("--project-dir", required=True, help="工程目录（绝对路径）")
ap.add_argument("--project", required=True, help="工程名，如 th16.exe")
ap.add_argument("--program", required=True, help="工程内程序路径，如 /th16.exe")
ap.add_argument("--out", required=True, help="输出 JSON 路径")
a = ap.parse_args()

# 只读打开：dump 不改库，也就不该有落盘这一步
with open_program(a.project_dir, a.project, a.program) as prog:
    out = []
    for f in prog.getFunctionManager().getFunctions(True):
        sym = f.getSymbol()
        out.append({
            "addr": "0x%08x" % f.getEntryPoint().getOffset(),
            "name": f.getName(),
            "size": f.getBody().getNumAddresses(),
            "xrefs": int(sym.getReferenceCount()) if sym is not None else 0,
            "thunk": bool(f.isThunk()),
            "external": bool(f.isExternal()),
        })
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    json.dump(out, open(a.out, "w"), indent=0)
    print("[dump_funcs] wrote %d functions -> %s" % (len(out), a.out))
