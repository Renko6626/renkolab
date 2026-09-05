#!/usr/bin/env python3
"""刷新 files.js —— thcrap 分发用的 {相对路径: crc32} 清单，递归子目录，收 .js / .anm / .ecl / .wav。

.wav 是音效表扩容的语音（patch/th18/voice/）：DLL 用 stack_game_file_resolve 取它们，
不进 files.js 的话远端分发时不会被下载。

    python3 mkfiles.py                 # patch/ 与 patch-test/
    python3 mkfiles.py <dir> [<dir>…]  # 只刷给定目录（make dist 对 dist/patch-step3 用）
"""
import subprocess
import sys
import json, os, zlib

HERE = os.path.dirname(os.path.abspath(__file__))


def gitignored(paths, patch_dir):
    """问 git 哪些文件是 gitignored 的 —— **入库的** files.js 不该列它们。

    语音 wav 在本仓是 gitignored 的（不留版权 / 大二进制字节），所以 patch/files.js
    不列它；而 make dist 的目标 dist/ **整个目录**就是 gitignored 的 —— 那份是要发出去的，
    必须全收。所以先看目录本身：被忽略 = 出包用，不过滤。
    """
    if not paths:
        return set()
    if subprocess.run(["git", "check-ignore", "-q", patch_dir], cwd=HERE).returncode == 0:
        return set()                       # dist/ 之类：整个目录在仓库之外，全收
    r = subprocess.run(["git", "check-ignore", "--stdin"], input="\n".join(paths),
                       capture_output=True, text=True, cwd=HERE)
    return set(r.stdout.split("\n")) - {""}


def refresh(patch_dir):
    cand = []
    for root, _dirs, names in os.walk(patch_dir):
        for name in sorted(names):
            full = os.path.join(root, name)
            rel = os.path.relpath(full, patch_dir).replace(os.sep, "/")
            if rel == "files.js" or not rel.endswith((".js", ".anm", ".ecl", ".wav", ".sht")):
                continue
            cand.append((rel, full))
    skip = gitignored([f for _, f in cand], patch_dir)
    out = {}
    for rel, full in cand:
        if full in skip:
            continue
        with open(full, "rb") as f:
            out[rel] = zlib.crc32(f.read()) & 0xffffffff
    with open(os.path.join(patch_dir, "files.js"), "w", encoding="utf-8") as f:
        json.dump(dict(sorted(out.items())), f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("%s/files.js:" % os.path.basename(patch_dir), out)


if len(sys.argv) > 1:
    for d in sys.argv[1:]:
        refresh(os.path.abspath(d))
else:
    for d in ("patch", "patch-test"):
        refresh(os.path.join(HERE, "..", d))
