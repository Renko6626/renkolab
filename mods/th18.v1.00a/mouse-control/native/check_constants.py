#!/usr/bin/env python3
"""把死绑量拿去和真 th18.exe 对账 —— 源码里的 `th18.h` 和 patch 里的断点声明都查。

这些常量是「某个 exe 的某几个字节」，抄错一位就静默失效（断点被 thcrap 跳过、
偏移读到邻居字段）。`make check` 会跑它；换 exe build 后它必须先过。

检查项：
  1. exe md5 是否是登记的那一份
  2. th18.h 里两处版本守卫签名 ↔ exe 实际字节
  3. 每个 patch 的 `breakpoints` 里的 addr / expected ↔ exe 实际字节
  4. cavesize 是否等于 expected 的字节数（不等则挪走的指令与校验的不是同一段）

用法：  python3 check_constants.py [path/to/th18.exe]
"""

import hashlib
import json
import re
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
DEFAULT_EXE = REPO / "local" / "th18.v1.00a" / "th18.exe"
EXPECTED_MD5 = "9969cac756098c1da05a81de45437a70"
HEADER = HERE / "th18.h"
DLL_MAIN = HERE / "dll_main.c"
PATCH_GLOB = sorted((HERE.parents[1]).glob("*/patch/th18.v1.00a.js"))


def sections(exe: bytes):
    pe = struct.unpack_from("<I", exe, 0x3C)[0]
    if exe[pe : pe + 4] != b"PE\0\0":
        raise SystemExit("不是 PE 文件")
    nsec = struct.unpack_from("<H", exe, pe + 6)[0]
    optsz = struct.unpack_from("<H", exe, pe + 20)[0]
    imagebase = struct.unpack_from("<I", exe, pe + 24 + 28)[0]
    out, off = [], pe + 24 + optsz
    for _ in range(nsec):
        vsz, va, rsz, raw = struct.unpack_from("<IIII", exe, off + 8)
        out.append((va, vsz, raw, rsz))
        off += 40
    return imagebase, out


def rva_to_off(secs, rva):
    for va, vsz, raw, rsz in secs:
        if va <= rva < va + max(vsz, rsz):
            return raw + (rva - va)
    return None


def define(text: str, name: str) -> int:
    m = re.search(r"#define\s+%s\s+(0x[0-9a-fA-F]+)" % name, text)
    if not m:
        raise SystemExit(f"找不到 #define {name}")
    return int(m.group(1), 16)


def sig_array(text: str, name: str) -> bytes:
    m = re.search(r"SIG_%s\[\]\s*=\s*\{(.*?)\}" % name, text, re.S)
    if not m:
        raise SystemExit(f"找不到 SIG_{name}")
    return bytes(int(x, 16) for x in re.findall(r"0x([0-9a-fA-F]{2})", m.group(1)))


def main() -> int:
    exe_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_EXE
    if not exe_path.exists():
        print(f"找不到样本 {exe_path} —— 样本由用户自备，见 local/README.md")
        return 2

    exe = exe_path.read_bytes()
    hdr = HEADER.read_text(encoding="utf-8")
    src = DLL_MAIN.read_text(encoding="utf-8")
    imagebase, secs = sections(exe)
    ok = True

    md5 = hashlib.md5(exe).hexdigest()
    print(f"exe   {exe_path}")
    if md5 == EXPECTED_MD5:
        print(f"md5   {md5}  ✅")
    else:
        ok = False
        print(f"md5   {md5}  ❌ 期望 {EXPECTED_MD5} —— 另一个 build，下面的量全部作废")

    print("\n[1] 版本守卫签名（th18.h RVA × dll_main.c 字节数组）")
    for name, macro in (("A", "RVA_SIG_A"), ("B", "RVA_SIG_B")):
        rva = define(hdr, macro)
        sig = sig_array(src, name)
        off = rva_to_off(secs, rva)
        real = exe[off : off + len(sig)] if off is not None else b""
        if sig == real:
            print(f"  SIG_{name}  VA 0x{imagebase + rva:x}  {len(sig)} 字节  ✅")
        else:
            ok = False
            print(f"  SIG_{name}  VA 0x{imagebase + rva:x}  ❌")
            print(f"          源码 {sig.hex(' ')}")
            print(f"          实读 {real.hex(' ')}")

    print("\n[2] patch 里的断点声明")
    if not PATCH_GLOB:
        print("  （没有找到任何 */patch/th18.v1.00a.js）")
    for js in PATCH_GLOB:
        data = json.loads(js.read_text(encoding="utf-8"))
        rel = js.relative_to(HERE.parents[1])
        for name, bp in (data.get("breakpoints") or {}).items():
            addr = int(str(bp["addr"]), 16)
            want = bytes.fromhex(str(bp["expected"]).replace(" ", ""))
            cavesize = bp.get("cavesize")
            off = rva_to_off(secs, addr - imagebase)
            real = exe[off : off + len(want)] if off is not None else b""
            tag = f"{rel}:{name}"
            if want != real:
                ok = False
                print(f"  {tag}  addr 0x{addr:x}  ❌ expected 与 exe 不符")
                print(f"          expected {want.hex(' ')}")
                print(f"          实读     {real.hex(' ')}")
            elif cavesize != len(want):
                ok = False
                print(f"  {tag}  ❌ cavesize {cavesize} != expected 的 {len(want)} 字节")
                print("          （挪走的指令与被校验的不是同一段，thcrap 会挪走多/少的字节）")
            else:
                print(f"  {tag}  addr 0x{addr:x}  cavesize {cavesize}  ✅")

    print("\n全部一致，死绑量与该 exe 对得上。" if ok else "\n有不一致 —— 不要拿去跑。")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
