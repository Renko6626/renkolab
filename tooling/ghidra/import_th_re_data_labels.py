#!/usr/bin/env python3
"""导入 th-re-data 的 `labels.json` —— VM 指令分发函数体内的 switch case 标签。

这是 ExpHP 数据里最容易被漏掉的一个文件（本仓在 2026-09-01 前从没读过它），
但对「搞懂 VM」这件事它的密度最高：每条 = 一个 **opcode → 处理分支地址**。

格式是 `{组: [[地址, "<opcode>__<名字>"], ...]}`，标签名按 ExpHP README 自己给的拼法
构造成 `<组>__case_<后缀>`。th18 五组 492 条：ecl 242 / anm 136 / msg 36 / std 21 / card 57。

导入后那些巨型 switch 反编译出来每个分支都带 opcode 名，等于白拿一张 opcode 表。
顺带在宿主函数上写一条 plate 注释登记「本函数含 N 个 <组> opcode case」——
这是从数据**推出来的**（我们自己数的），不是转发 ExpHP 的内容。

    python import_th_re_data_labels.py <DATA_DIR> --project-dir DIR --project NAME --program /prog

safe 模式：同地址同名标签已存在就跳过，绝不改已有符号。`--dry-run` 只统计。
"""
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _driver import add_project_args, open_program  # noqa: E402


def label_name(group, suffix):
    """ExpHP README 给的拼法：'std__case_0__posKeyframe'。"""
    return f"{group}__case_{suffix}"


def apply(prog, data_dir, dry=False, overwrite=False):
    from ghidra.program.model.listing import CodeUnit
    from ghidra.program.model.symbol import SourceType

    US = SourceType.USER_DEFINED
    addr = prog.getAddressFactory().getDefaultAddressSpace().getAddress
    st, fm, lst = prog.getSymbolTable(), prog.getFunctionManager(), prog.getListing()

    path = os.path.join(data_dir, "labels.json")
    if not os.path.exists(path):
        print("[labels] 没有 labels.json，跳过")
        return dict(created=0, skipped=0, unmapped=0, hosts=0, comments=0)

    n = dict(created=0, skipped=0, unmapped=0, hosts=0, comments=0)
    hosts = Counter()          # (宿主函数入口, 组) -> case 数

    for group, rows in json.load(open(path, encoding="utf-8")).items():
        for a_hex, suffix in rows:
            a = addr(int(a_hex, 16))
            blk = prog.getMemory().getBlock(a)
            if blk is None:
                n["unmapped"] += 1
                continue
            want = label_name(group, suffix)
            if any(s.getName() == want for s in st.getSymbols(a)):
                n["skipped"] += 1
            else:
                if not dry:
                    st.createLabel(a, want, US)
                n["created"] += 1
            f = fm.getFunctionContaining(a)
            if f is not None:
                hosts[(f.getEntryPoint(), group)] += 1

    # 宿主函数上登记「含 N 个 <组> opcode case」——我们数出来的，不是 ExpHP 的原文
    per_func = {}
    for (entry, group), cnt in hosts.items():
        per_func.setdefault(entry, []).append((group, cnt))
    for entry, groups in per_func.items():
        n["hosts"] += 1
        text = "[th-re-data] " + "；".join(
            f"含 {cnt} 个 {group} opcode case（labels.json）" for group, cnt in sorted(groups))
        if lst.getComment(CodeUnit.PLATE_COMMENT, entry) is not None and not overwrite:
            continue
        if not dry:
            lst.setComment(entry, CodeUnit.PLATE_COMMENT, text)
        n["comments"] += 1
    return n


def _summary(n, dry):
    print(("[dry-run] " if dry else "") + "[th-re-data labels] " +
          " ".join(f"{k}={v}" for k, v in n.items()))


if __name__ == "__main__":
    cp = globals().get("currentProgram")          # 只在 Ghidra 脚本上下文里注入
    if cp is not None:                            # mode A: 在 Ghidra 里跑（工具自己管 tx + save）
        args = list(getScriptArgs())              # noqa: F821
        dry = "--dry-run" in args
        dd = next((a for a in args if not a.startswith("-")), None) \
            or askDirectory("th-re-data dir", "Select").getPath()    # noqa: F821
        _summary(apply(cp, dd, dry, "--overwrite" in args), dry)
    else:                                         # mode B: 独立 PyGhidra driver
        import argparse
        ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
        ap.add_argument("data_dir")
        add_project_args(ap)
        ap.add_argument("--overwrite", action="store_true", help="覆盖宿主函数上已有的 plate 注释")
        a = ap.parse_args()
        with open_program(a.project_dir, a.project, a.program,
                          tx="import th-re-data labels", commit=not a.dry_run) as prog:
            n = apply(prog, a.data_dir, a.dry_run, a.overwrite)
        _summary(n, a.dry_run)
