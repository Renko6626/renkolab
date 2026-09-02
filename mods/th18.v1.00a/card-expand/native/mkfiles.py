#!/usr/bin/env python3
"""刷新 patch/files.js —— thcrap 分发用的 {路径: crc32} 清单。"""
import json, os, zlib

HERE  = os.path.dirname(os.path.abspath(__file__))
PATCH = os.path.join(HERE, "..", "patch")

out = {}
for name in sorted(os.listdir(PATCH)):
    if name in ("files.js",) or not name.endswith(".js"):
        continue
    with open(os.path.join(PATCH, name), "rb") as f:
        out[name] = zlib.crc32(f.read()) & 0xffffffff
with open(os.path.join(PATCH, "files.js"), "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)
    f.write("\n")
print("files.js:", out)
