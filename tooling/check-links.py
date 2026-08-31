#!/usr/bin/env python3
"""检查仓库里所有 markdown 相对链接是否可解析。

大规模 git mv 之后相对链接必断，而本仓库文档互相引用极密，所以这个检查是硬性的。

    python tooling/check-links.py            # 检查，有断链则 exit 1
    python tooling/check-links.py --list     # 顺带列出没有任何入链的文档（孤儿）
"""
import argparse, re, subprocess, sys
from pathlib import Path
from urllib.parse import unquote

REPO = Path(__file__).resolve().parents[1]
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
SKIP = re.compile(r"^(https?:|mailto:|#|<)")
# 目标必须"像路径"才算链接 —— 散文里的 vtable[13](1)、on_sprite_set[4](`x`) 不是。
PATHISH = re.compile(r"(/|\.(md|py|sh|json|txt|js|c|h|asm|diff|sht|msg|ecl|anm|toml|yml)$)", re.I)
FENCE = re.compile(r"^\s*(```|~~~)", re.M)
INLINE_CODE = re.compile(r"`[^`\n]*`")


def strip_code(text):
    """去掉围栏代码块与行内代码 —— 里面的 `foo[i](1)` 不是链接。"""
    out, in_fence = [], False
    for line in text.split("\n"):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        out.append("" if in_fence else INLINE_CODE.sub("``", line))
    return "\n".join(out)


def tracked_md():
    # -z：NUL 分隔且不转义非 ASCII 路径（默认会把中文文件名加引号转义）
    out = subprocess.run(["git", "-C", str(REPO), "ls-files", "-z", "*.md"],
                         capture_output=True, text=True, check=True).stdout
    return [REPO / p for p in out.split("\0") if p]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--list", action="store_true", help="同时报告孤儿文档")
    a = ap.parse_args()

    files = tracked_md()
    broken, inbound = [], {f: 0 for f in files}

    for f in files:
        for m in LINK.finditer(strip_code(f.read_text(encoding="utf-8", errors="replace"))):
            raw = m.group(1)
            if SKIP.match(raw):
                continue
            target = unquote(raw.split("#", 1)[0])
            if not target or not PATHISH.search(target):
                continue
            dest = (f.parent / target).resolve()
            if not dest.exists():
                broken.append((f.relative_to(REPO), raw))
            elif dest in inbound:
                inbound[dest] += 1

    if broken:
        print(f"✗ {len(broken)} 条断链：\n")
        for src, raw in broken:
            print(f"  {src}\n      -> {raw}")
    else:
        print(f"✓ {len(files)} 个 markdown 文件，所有相对链接可解析")

    if a.list:
        orphans = [f.relative_to(REPO) for f, n in inbound.items()
                   if n == 0 and f.name not in ("README.md", "CLAUDE.md", "METHOD.md", "INDEX.md")]
        if orphans:
            print(f"\n⚠ {len(orphans)} 个文档没有任何入链：")
            for o in sorted(orphans):
                print(f"  {o}")

    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
