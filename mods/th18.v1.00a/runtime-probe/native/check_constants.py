#!/usr/bin/env python3
"""把 th18_probe.c 里写死的签名字节与 RVA 拿去和真 th18.exe 对账。

用途：这些常量是「某个 exe 的某几个字节」，抄错一位探针就静默失效。
`make check` 会跑它；换 exe build 后它必须先过，才谈得上重跑探针。

用法：  python3 check_constants.py [path/to/th18.exe]
默认样本路径 local/th18.v1.00a/th18.exe（gitignored，见 local/README.md）。
"""

import re
import struct
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
DEFAULT_EXE = REPO / "local" / "th18.v1.00a" / "th18.exe"
EXPECTED_MD5 = "9969cac756098c1da05a81de45437a70"
SRC = Path(__file__).with_name("th18_probe.c")


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


def sig_array(src: str, name: str) -> bytes:
    m = re.search(r"SIG_%s\[\]\s*=\s*\{(.*?)\}" % name, src, re.S)
    if not m:
        raise SystemExit(f"源码里找不到 SIG_{name}")
    return bytes(int(x, 16) for x in re.findall(r"0x([0-9a-fA-F]{2})", m.group(1)))


def define(src: str, name: str) -> int:
    m = re.search(r"#define\s+%s\s+(0x[0-9a-fA-F]+)" % name, src)
    if not m:
        raise SystemExit(f"源码里找不到 #define {name}")
    return int(m.group(1), 16)


def main() -> int:
    import hashlib

    exe_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_EXE
    if not exe_path.exists():
        print(f"找不到样本 {exe_path} —— 样本由用户自备，见 local/README.md")
        return 2

    exe = exe_path.read_bytes()
    src = SRC.read_text(encoding="utf-8")
    md5 = hashlib.md5(exe).hexdigest()
    imagebase, secs = sections(exe)

    ok = True
    print(f"exe        {exe_path}")
    if md5 == EXPECTED_MD5:
        print(f"md5        {md5}  ✅")
    else:
        print(f"md5        {md5}  ❌ 期望 {EXPECTED_MD5} —— 这是另一个 build，下面的量全部作废")
        ok = False

    for name, macro in (("A", "RVA_SIG_A"), ("B", "RVA_SIG_B")):
        rva = define(src, macro)
        sig = sig_array(src, name)
        off = rva_to_off(secs, rva)
        real = exe[off : off + len(sig)] if off is not None else b""
        if sig == real:
            print(f"SIG_{name}      VA 0x{imagebase + rva:x}  {len(sig)} 字节  ✅")
        else:
            ok = False
            print(f"SIG_{name}      VA 0x{imagebase + rva:x}  ❌")
            print(f"             源码 {sig.hex(' ')}")
            print(f"             实读 {real.hex(' ')}")

    ptr = imagebase + define(src, "RVA_PLAYER_PTR")
    print(f"PLAYER_PTR VA 0x{ptr:x}  {'✅' if ptr == 0x4CF410 else '❌ 与 ExpHP statics 的 0x4cf410 不符'}")
    ok &= ptr == 0x4CF410

    print("\n全部一致，探针的死绑量与该 exe 对得上。" if ok else "\n有不一致 —— 不要拿去跑。")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
