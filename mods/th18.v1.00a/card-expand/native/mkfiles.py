#!/usr/bin/env python3
"""刷新 files.js —— thcrap 分发用的 {相对路径: crc32} 清单，递归子目录，收 .js / .anm / .ecl / .wav。

.wav 是音效表扩容的语音（patch/th18/voice/）：DLL 用 stack_game_file_resolve 取它们，
不进 files.js 的话远端分发时不会被下载。

    python3 mkfiles.py                 # patch/ 与 patch-test/
    python3 mkfiles.py <dir> [<dir>…]  # 只刷给定目录（make dist 对 dist/patch-step3 用）
"""
import sys
import json, os, zlib

HERE = os.path.dirname(os.path.abspath(__file__))


def refresh(patch_dir):
    out = {}
    for root, _dirs, names in os.walk(patch_dir):
        for name in sorted(names):
            rel = os.path.relpath(os.path.join(root, name), patch_dir).replace(os.sep, "/")
            if rel == "files.js" or not rel.endswith((".js", ".anm", ".ecl", ".wav")):
                continue
            with open(os.path.join(root, name), "rb") as f:
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
