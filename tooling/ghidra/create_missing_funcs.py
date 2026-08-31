#!/usr/bin/env python3
"""在 ExpHP 标了函数、而 Ghidra 没建函数的地址上补建函数。

自动分析只跟得到「被 call 到」的代码。只经 **vtable / 函数指针表** 进入的回调
（`*::on_tick` / `*::on_draw` 那批 stub）和 CRT 的 `life_before_main__*` 初始化器
在 Ghidra 眼里往往还是未定义字节，于是 `import_th_re_data.py` 在
`getFunctionAt()` 上拿到 None，把它们记成 `missing=N` 丢掉——TH18 首次 bootstrap
就这样漏掉 63 个，其中包括 `Player::on_tick`、`BulletManager::on_tick`。

本脚本按 ExpHP 的 funcs.json 逐地址补：没指令就先反汇编，再 CreateFunctionCmd。
跑完再跑一遍 import_th_re_data.py，那批名字就落得上了。

    python create_missing_funcs.py <DATA_DIR> --project-dir DIR --project NAME --program /prog

`--dry-run` 只统计不写库。落在**已有函数体内部**的地址一律跳过并计入 `inside=`——
那多半是 ExpHP 与 Ghidra 对函数边界的分歧，不该盲目切开。
"""
import json, os


def apply(prog, data_dir, dry=False):
    from ghidra.app.cmd.disassemble import DisassembleCommand
    from ghidra.app.cmd.function import CreateFunctionCmd
    from ghidra.util.task import ConsoleTaskMonitor

    addr = prog.getAddressFactory().getDefaultAddressSpace().getAddress
    fm, lst, mem = prog.getFunctionManager(), prog.getListing(), prog.getMemory()
    mon = ConsoleTaskMonitor()
    n = dict(created=0, existed=0, inside=0, disassembled=0, unmapped=0, failed=0)

    path = os.path.join(data_dir, "funcs.json")
    if not os.path.exists(path):
        return n
    for r in json.load(open(path, encoding="utf-8")):
        a = addr(int(r["addr"], 16))
        if fm.getFunctionAt(a) is not None:
            n["existed"] += 1
            continue
        blk = mem.getBlock(a)
        if blk is None or not blk.isExecute():
            n["unmapped"] += 1
            continue
        if fm.getFunctionContaining(a) is not None:
            n["inside"] += 1                    # ExpHP 与 Ghidra 的函数边界分歧，不切
            continue
        if dry:
            n["created"] += 1
            continue
        if lst.getInstructionAt(a) is None:
            if DisassembleCommand(a, None, True).applyTo(prog, mon):
                n["disassembled"] += 1
        if lst.getInstructionAt(a) is None:
            n["failed"] += 1
            continue
        if CreateFunctionCmd(a).applyTo(prog, mon) and fm.getFunctionAt(a) is not None:
            n["created"] += 1
        else:
            n["failed"] += 1
    return n


def _summary(n, dry):
    print(("[dry-run] " if dry else "") + "[create-missing] " +
          " ".join("%s=%d" % (k, v) for k, v in n.items()))


if __name__ == "__main__":
    cp = globals().get("currentProgram")          # 只在 Ghidra 脚本上下文里注入
    if cp is not None:                            # mode A: 在 Ghidra 里跑（工具自己管 tx + save）
        args = list(getScriptArgs())              # noqa: F821
        dry = "--dry-run" in args
        dd = next((a for a in args if not a.startswith("-")), None) \
            or askDirectory("th-re-data dir", "Select").getPath()    # noqa: F821
        _summary(apply(cp, dd, dry), dry)
    else:                                         # mode B: 独立 PyGhidra driver
        import argparse, sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from _driver import add_project_args, open_program
        ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
        ap.add_argument("data_dir")
        add_project_args(ap)
        a = ap.parse_args()
        with open_program(a.project_dir, a.project, a.program,
                          tx="create missing th-re-data functions", commit=not a.dry_run) as prog:
            n = apply(prog, a.data_dir, a.dry_run)
        _summary(n, a.dry_run)
