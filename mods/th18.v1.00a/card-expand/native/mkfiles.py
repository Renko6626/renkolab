#!/usr/bin/env python3
"""刷新 patch/ 与 patch-test/ 的 files.js —— thcrap 分发用的 {相对路径: crc32} 清单。递归子目录（th18/cards.js）。"""
import json, os, zlib

HERE = os.path.dirname(os.path.abspath(__file__))


def refresh(patch_dir):
    out = {}
    for root, _dirs, names in os.walk(patch_dir):
        for name in sorted(names):
            rel = os.path.relpath(os.path.join(root, name), patch_dir).replace(os.sep, "/")
            if rel == "files.js" or not rel.endswith(".js"):
                continue
            with open(os.path.join(root, name), "rb") as f:
                out[rel] = zlib.crc32(f.read()) & 0xffffffff
    with open(os.path.join(patch_dir, "files.js"), "w", encoding="utf-8") as f:
        json.dump(dict(sorted(out.items())), f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("%s/files.js:" % os.path.basename(patch_dir), out)


for d in ("patch", "patch-test"):
    refresh(os.path.join(HERE, "..", d))
