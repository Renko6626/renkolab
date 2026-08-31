#!/usr/bin/env python3
"""把 exe 里的 Shift-JIS 字符串认出来并定义掉。

Ghidra 的字符串分析器对 Shift-JIS 基本无能为力——日文串要么没被识别，要么被当成
float 显示成 `5.16662e+30` 那种荒唐数值（`0x4b7c14` 的 `82 6c 82 72` 其实是「ＭＳ」，
字体名 "ＭＳ 明朝" 的开头）。th18 实测：整个 exe 里 22 条真日文串一条都没被认出来。

判据两条，缺一不可：

1. **解码后按 Unicode 区段判**，不是按字节合法性判。.rdata 里的 double 浮点表
   碰巧也能解成「合法」Shift-JIS，只有要求解出来的字符落在平/片假名、汉字、
   全角标点区，才排得掉。
2. **前一字节必须是 NUL**。真 C 字符串是背靠背带 NUL 摆的；浮点表里碰巧解得通的
   垃圾不会这么对齐。这一条把 29 个候选压到 24 个，砍掉的全是假阳性。

    python import_sjis_strings.py <DATA_DIR 占位> --project-dir DIR --project NAME --program /prog
    python import_sjis_strings.py --list th18        # 只扫不写，看看有什么

**只在未定义字节上落**，已定义的一律跳过并计数——不覆盖任何人的东西。
落库之后 HTML 导出和 MCP 的 `get_strings` 会同时看到（两边都读 listing 的
`hasStringValue()`），对等自动成立。

产物属于**重放层**：给定 exe 结果唯一，所以 bootstrap 每次重跑即可，不进
`games/<版本>/symbols.json`。
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _driver import add_project_args, open_program, resolve          # noqa: E402

SCAN_BLOCKS = (".rdata", ".data")
CAND = re.compile(rb"[\x20-\xfc]{4,300}\x00")


def _is_jp(ch):
    c = ord(ch)
    return (0x3040 <= c <= 0x309F        # 平假名
            or 0x30A0 <= c <= 0x30FF     # 片假名
            or 0x4E00 <= c <= 0x9FFF     # 汉字
            or 0x3000 <= c <= 0x303F     # 全角标点
            or 0xFF01 <= c <= 0xFF60)    # 全角 ASCII


def _is_halfkana(ch):
    return 0xFF61 <= ord(ch) <= 0xFF9F   # 半角片假名：二进制垃圾里太常见，用来排除


MIN_BYTES = 6      # 至少 3 个双字节字符的量。低于这个的全是浮点表里的巧合
                   # （th18 实测：`眷ぞ` 5 字节、`蠅陲[` 5 字节 —— 三个假阳性都在 6 以下，
                   #  而最短的真串 `『%s』` 正好 6 字节）


def scan_block(data, base, min_jp=2):
    """在一块内存里找 Shift-JIS 串。返回 [(地址, 文本, 字节长度)]。"""
    out = []
    for m in CAND.finditer(data):
        start = m.start()
        if start > 0 and data[start - 1] != 0:
            continue                                  # 判据 2：前一字节必须是 NUL
        raw = m.group()[:-1]
        try:
            text = raw.decode("shift_jis")
        except Exception:
            continue
        jp = sum(1 for c in text if _is_jp(c))
        hk = sum(1 for c in text if _is_halfkana(c))
        asc = sum(1 for c in text if 0x20 <= ord(c) < 0x7F)
        if (jp >= min_jp and hk <= 1 and len(raw) >= MIN_BYTES
                and (jp + asc) / max(1, len(text)) > 0.9):
            out.append((base + start, text, len(raw) + 1))
    return out


def find_all(prog, min_jp=2):
    import jpype
    mem = prog.getMemory()
    hits = []
    for blk in mem.getBlocks():
        if blk.getName() not in SCAN_BLOCKS or not blk.isInitialized():
            continue
        size = int(blk.getSize())
        buf = jpype.JArray(jpype.JByte)(size)
        mem.getBytes(blk.getStart(), buf)
        data = bytes((b & 0xFF) for b in buf)
        hits += scan_block(data, blk.getStart().getOffset(), min_jp)
    hits.sort()
    return hits


def apply(prog, dry=False, min_jp=2, verbose=False):
    from ghidra.program.model.data import (TerminatedStringDataType, DataUtilities,
                                           CharsetSettingsDefinition)
    from ghidra.program.model.data.DataUtilities import ClearDataMode

    af = prog.getAddressFactory().getDefaultAddressSpace().getAddress
    lst = prog.getListing()
    n = dict(found=0, applied=0, already=0, occupied=0, failed=0)

    for addr, text, _sz in find_all(prog, min_jp):
        n["found"] += 1
        ad = af(addr)
        cur = lst.getDataAt(ad)
        # ⚠️ Ghidra 的 undefined1/2/4/8 是**占位类型**，isDefined() 却返回 True。
        # 把它们当「已定义」会误伤——th18 有两条串就卡在 undefined8 上。占位可以覆盖，
        # 别人真正定义过的（string / 结构体 / 具体标量）才不碰。
        if cur is not None and cur.isDefined() \
                and not cur.getDataType().getName().startswith("undefined"):
            n["already" if cur.hasStringValue() else "occupied"] += 1
            continue
        if verbose or dry:
            print("   0x%08x  %s" % (addr, text[:70]))
        if dry:
            n["applied"] += 1
            continue
        try:
            d = DataUtilities.createData(prog, ad, TerminatedStringDataType.dataType, -1,
                                         ClearDataMode.CLEAR_ALL_UNDEFINED_CONFLICT_DATA)
            CharsetSettingsDefinition.CHARSET.setCharset(d, "Shift_JIS")
            n["applied"] += 1
            continue
        except Exception as e:                        # noqa: BLE001
            first_err = str(e)[:120]

        # 落不上通常只有一种情况：Ghidra 的 ASCII 分析器把这条串的**尾巴**（纯 ASCII 那截）
        # 单独定义成了一个 string，占住地盘。那玩意儿是我们这条串的片段，不是别人的成果——
        # 确认「所有冲突项都是完全落在本串范围内的字符串」之后才让路，其余一律不碰。
        if _only_contained_strings(lst, ad, _sz):
            try:
                d = DataUtilities.createData(prog, ad, TerminatedStringDataType.dataType, -1,
                                             ClearDataMode.CLEAR_ALL_CONFLICT_DATA)
                CharsetSettingsDefinition.CHARSET.setCharset(d, "Shift_JIS")
                n["applied"] += 1
                if verbose:
                    print("      （清掉了范围内的 ASCII 片段串）")
                continue
            except Exception as e:                    # noqa: BLE001
                first_err = str(e)[:120]
        n["failed"] += 1
        if verbose:
            print("   !! 0x%08x 落不上：%s" % (addr, first_err))
    return n


def _only_contained_strings(lst, start, size):
    """范围内的已定义数据是否**全都**是完全落在范围内的字符串。"""
    end = start.add(size - 1)
    ad, saw = start, False
    while ad.compareTo(end) <= 0:
        d = lst.getDataAt(ad)
        if d is None:
            return False
        if d.isDefined() and not d.getDataType().getName().startswith("undefined"):
            if not d.hasStringValue():
                return False                          # 不是串 → 别人的东西，不碰
            if d.getMaxAddress().compareTo(end) > 0:
                return False                          # 伸到范围外 → 不是我们的片段
            saw = True
        ad = ad.add(max(1, d.getLength()))
    return saw


def _summary(n, dry):
    print(("[dry-run] " if dry else "") + "[sjis] " +
          " ".join(f"{k}={v}" for k, v in n.items()))


if __name__ == "__main__":
    cp = globals().get("currentProgram")          # 只在 Ghidra 脚本上下文里注入
    if cp is not None:                            # mode A: 在 Ghidra 里跑
        args = list(getScriptArgs())              # noqa: F821
        _summary(apply(cp, "--dry-run" in args), "--dry-run" in args)
    elif "--list" in sys.argv:                    # mode C: 只扫不写
        ap = argparse.ArgumentParser()
        ap.add_argument("--list", action="store_true")
        ap.add_argument("version")
        ap.add_argument("--min-jp", type=int, default=2)
        a = ap.parse_args()
        P = resolve(a.version)
        with open_program(P["proj_dir"].resolve(), P["proj_name"], P["program"]) as prog:
            hits = find_all(prog, a.min_jp)
        for addr, text, _ in hits:
            print("0x%08x  %s" % (addr, text))
        print("[sjis] 共 %d 条" % len(hits))
    else:                                         # mode B: 独立 PyGhidra driver
        ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
        ap.add_argument("data_dir", nargs="?", help="不用，只为与其他 importer 同形")
        add_project_args(ap)
        ap.add_argument("--min-jp", type=int, default=2,
                        help="至少几个日文字符才算（默认 2；调到 3 更严但会漏掉 『%%s』 这种）")
        ap.add_argument("--verbose", action="store_true")
        a = ap.parse_args()
        with open_program(a.project_dir, a.project, a.program,
                          tx="import shift-jis strings", commit=not a.dry_run) as prog:
            n = apply(prog, a.dry_run, a.min_jp, a.verbose)
        _summary(n, a.dry_run)
