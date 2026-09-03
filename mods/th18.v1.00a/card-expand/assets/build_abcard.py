#!/usr/bin/env python3
"""把 cards/ 里的新卡图追加进零售 abcard.anm，重编到 native/build/abcard.anm，并校验。

    python3 build_abcard.py                # 构建 + 自检 + 校验 cards.js 索引
    python3 build_abcard.py --verify-only  # 只自检已有的 build/abcard.anm

索引规则：cards/ORDER.txt 第 k 行（0 起）→ sprite_large = base + 2k，sprite_small = base + 2k + 1，
base = 零售 entry 数（th18 = 118）。零售 spec / 贴图取自 local/th18.v1.00a/anm/abcard/
（tooling/thtk/unpack.py 解出的）；工具与 anmmap 复用 tooling/thtk/unpack.py 的 find_tools()。

新 entry 的字段照抄 BLANK_max / BLANK_min（只换 name 与 sprite 号）；_min 源图 64×80 垫成
64×128 透明底（THTX 高 128）。任何校验不过 → exit 1，**不会**去改 JSON。
"""
import argparse
import filecmp
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent            # assets/
MOD = HERE.parent                                 # card-expand/
REPO = MOD.parents[2]                             # renkolab/
sys.path.insert(0, str(REPO / "tooling" / "thtk"))

VERSION = "18"
RETAIL_DIR = REPO / "local" / "th18.v1.00a" / "anm" / "abcard"
RETAIL_SPEC = RETAIL_DIR / "abcard.anm.txt"
ORDER = HERE / "cards" / "ORDER.txt"
CARDS_JS = MOD / "patch" / "th18" / "cards.js"
BUILD = MOD / "native" / "build"
TEX = BUILD / "tex"
OUT_ANM = BUILD / "abcard.anm"
TEMPLATES = {"max": "ability/BLANK_max.png", "min": "ability/BLANK_min.png"}

_ENTRY = re.compile(r"^entry entry(\d+) \{\n(.*?)^\}\n?", re.S | re.M)
_FIELD = re.compile(r"^\s{4}(\w+): (.+),$", re.M)
_SPRITE = re.compile(r"sprite(\d+): \{ x: (\S+), y: (\S+), w: (\S+), h: (\S+) \}")


# ── 纯函数（有单测：native/tests/test_build_abcard.py）───────────────────
def parse_entries(spec_text: str):
    """→ [{idx, name, keys, fields, sprite, block, span}]；fields 不含 name，keys 记字段顺序（含 name）。"""
    out = []
    for m in _ENTRY.finditer(spec_text):
        body = m.group(2)
        head = body.split("    sprites: {", 1)[0]
        keys, fields, name = [], {}, None
        for fm in _FIELD.finditer(head):
            k, v = fm.group(1), fm.group(2)
            keys.append(k)
            if k == "name":
                name = v.strip('"')
            else:
                fields[k] = v
        sprites = _SPRITE.findall(body)
        if len(sprites) != 1:
            raise SystemExit(f"entry{m.group(1)} 有 {len(sprites)} 个 sprite，本脚本只处理一 entry 一 sprite 的 abcard.anm")
        s = sprites[0]
        out.append({"idx": int(m.group(1)), "name": name, "keys": keys, "fields": fields,
                    "sprite": {"x": s[1], "y": s[2], "w": s[3], "h": s[4]},
                    "block": m.group(0), "span": m.span()})
    return out


def make_entry(template: dict, idx: int, png_rel: str) -> str:
    """照抄模板字段，只换 name 与 sprite 号。"""
    lines = [f"entry entry{idx} {{"]
    for k in template["keys"]:
        v = f'"{png_rel}"' if k == "name" else template["fields"][k]
        lines.append(f"    {k}: {v},")
    s = template["sprite"]
    lines += ["    sprites: {",
              f"        sprite{idx}: {{ x: {s['x']}, y: {s['y']}, w: {s['w']}, h: {s['h']} }}",
              "    }", "}", ""]
    return "\n".join(lines)


def expected_sprites(order, base: int):
    return {name: (base + 2 * k, base + 2 * k + 1) for k, name in enumerate(order)}


def check_cards_js(cards: dict, expected: dict, n_entries: int, base: int):
    """→ 错误行列表。规则：索引都 < n_entries；ORDER 里的卡必须等于推出的对；不在 ORDER 的卡只能用零售索引（< base）。"""
    errs = []
    for cid, c in cards.items():
        nm = c.get("internal_name", "?")
        pair = (c.get("sprite_large"), c.get("sprite_small"))
        if any(p is None for p in pair):
            continue
        if any(p >= n_entries or p < 0 for p in pair):
            errs.append(f"卡 {cid} ({nm}): sprite {pair} 越界（entry 数 {n_entries}）")
        if nm in expected:
            if pair != expected[nm]:
                errs.append(f"卡 {cid} ({nm}): JSON 填的是 {pair}，ORDER 推出应为 {expected[nm]}")
        elif any(p >= base for p in pair):
            errs.append(f"卡 {cid} ({nm}): 用了新索引 {pair} 但 ORDER.txt 里没有它")
    return errs


def insert_entries(spec_text: str, blocks) -> str:
    """把新 entry 块插在最后一个 entry 之后、第一个 script 之前。"""
    entries = parse_entries(spec_text)
    if not entries:
        raise SystemExit("spec 里没有 entry")
    end = entries[-1]["span"][1]
    return spec_text[:end] + "\n" + "\n".join(b.rstrip("\n") + "\n" for b in blocks) + spec_text[end:]


# ── I/O ────────────────────────────────────────────────────────────────
def read_order():
    if not ORDER.is_file():
        raise SystemExit(f"没有 {ORDER}")
    names = [l.strip() for l in ORDER.read_text().splitlines() if l.strip() and not l.lstrip().startswith("#")]
    dup = {n for n in names if names.count(n) > 1}
    if dup:
        raise SystemExit(f"ORDER.txt 有重复：{sorted(dup)}")
    return names


def read_cards_js():
    if not CARDS_JS.is_file():
        raise SystemExit(f"没有 {CARDS_JS}")
    return json.loads(CARDS_JS.read_text(encoding="utf-8"))


def thanm(args, cwd, tools):
    r = subprocess.run([tools[0], *args], cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0 or r.stderr.strip():
        raise SystemExit(f"thanm {' '.join(map(str, args))} 失败：\n{r.stderr or r.stdout}")
    return r.stdout


def prepare_textures(order, tpl_max, tpl_min, retail_entries):
    """新图校验 / 垫底 → build/tex/ability/；零售贴图软链进来（thanm -c 的路径相对 cwd）。"""
    from PIL import Image
    want_max = (int(tpl_max["fields"]["THTXWidth"]), int(tpl_max["fields"]["THTXHeight"]))   # 256×320
    want_min = (int(tpl_min["sprite"]["w"]), int(tpl_min["sprite"]["h"]))                     # 64×80
    pad_min = (int(tpl_min["fields"]["THTXWidth"]), int(tpl_min["fields"]["THTXHeight"]))    # 64×128
    if TEX.exists():
        shutil.rmtree(TEX)
    (TEX / "ability").mkdir(parents=True)
    for e in retail_entries:
        dst = TEX / e["name"]
        src = RETAIL_DIR / e["name"]
        if not src.is_file():
            raise SystemExit(f"零售贴图缺 {src}：先 python3 tooling/thtk/unpack.py th18.v1.00a")
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            os.symlink(src, dst)
    for name in order:
        big, small = HERE / "cards" / f"{name}_max.png", HERE / "cards" / f"{name}_min.png"
        for p in (big, small):
            if not p.is_file():
                raise SystemExit(f"缺 {p}")
        im = Image.open(big).convert("RGBA")
        if im.size != want_max:
            raise SystemExit(f"{big.name} 是 {im.size}，要 {want_max}")
        im.save(TEX / "ability" / f"{name}_max.png")
        im = Image.open(small).convert("RGBA")
        if im.size != want_min:
            raise SystemExit(f"{small.name} 是 {im.size}，要 {want_min}")
        canvas = Image.new("RGBA", pad_min, (0, 0, 0, 0))
        canvas.paste(im, (0, 0))
        canvas.save(TEX / "ability" / f"{name}_min.png")


def build(order, tools, anmmap):
    spec_text = RETAIL_SPEC.read_text()
    retail = parse_entries(spec_text)
    base = len(retail)
    by_name = {e["name"]: e for e in retail}
    tpl_max, tpl_min = by_name[TEMPLATES["max"]], by_name[TEMPLATES["min"]]
    prepare_textures(order, tpl_max, tpl_min, retail)
    blocks = []
    for name, (lg, sm) in expected_sprites(order, base).items():
        blocks.append(make_entry(tpl_max, lg, f"ability/{name}_max.png"))
        blocks.append(make_entry(tpl_min, sm, f"ability/{name}_min.png"))
    (TEX / "abcard.spec").write_text(insert_entries(spec_text, blocks))
    if OUT_ANM.exists():
        OUT_ANM.unlink()
    thanm(["-c", VERSION, OUT_ANM, "abcard.spec", "-m", anmmap], TEX, tools)
    return base


def verify(order, tools, anmmap):
    """重建文件自检；返回 (base, n_entries)。"""
    if not OUT_ANM.is_file():
        raise SystemExit(f"没有 {OUT_ANM}：先 make anm")
    retail = parse_entries(RETAIL_SPEC.read_text())
    base = len(retail)
    by_name = {e["name"]: e for e in retail}
    rebuilt = parse_entries(thanm(["-l", VERSION, OUT_ANM, "-m", anmmap], BUILD, tools))
    want = base + 2 * len(order)
    if len(rebuilt) != want:
        raise SystemExit(f"entry 数 {len(rebuilt)}，应为 {base} + 2×{len(order)} = {want}")
    for i, (a, b) in enumerate(zip(retail, rebuilt)):
        if a["block"] != b["block"]:
            raise SystemExit(f"零售 entry{i} 的 spec 变了：\n{a['block']}\n→\n{b['block']}")
    exp = expected_sprites(order, base)
    for name, (lg, sm) in exp.items():
        for idx, kind, tpl in ((lg, "max", by_name[TEMPLATES["max"]]), (sm, "min", by_name[TEMPLATES["min"]])):
            e = rebuilt[idx]
            if e["idx"] != idx or e["name"] != f"ability/{name}_{kind}.png" or e["fields"] != tpl["fields"] or e["sprite"] != tpl["sprite"]:
                raise SystemExit(f"新 entry{idx}（{name}_{kind}）字段与 BLANK 模板不一致")
    with tempfile.TemporaryDirectory(dir=BUILD) as td:
        thanm(["-x", VERSION, OUT_ANM], td, tools)
        bad = [e["name"] for e in retail if not filecmp.cmp(Path(td) / e["name"], RETAIL_DIR / e["name"], shallow=False)]
        if bad:
            raise SystemExit(f"零售贴图被改动：{bad[:5]}{' …' if len(bad) > 5 else ''}")
    errs = check_cards_js(read_cards_js(), exp, len(rebuilt), base)
    if errs:
        raise SystemExit("cards.js 索引校验不过：\n  " + "\n  ".join(errs))
    return base, len(rebuilt)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--verify-only", action="store_true")
    a = ap.parse_args()
    from unpack import find_tools  # noqa: E402  —— tooling/thtk/unpack.py
    th, td, mapdir = find_tools()
    tools, anmmap = (th, td), mapdir / "v8.anmm"
    if not RETAIL_SPEC.is_file():
        raise SystemExit(f"没有 {RETAIL_SPEC}：先 python3 tooling/thtk/unpack.py th18.v1.00a")
    order = read_order()
    if not a.verify_only:
        base = build(order, tools, anmmap)
        print(f"build: {OUT_ANM.relative_to(MOD)}（{OUT_ANM.stat().st_size:,} B）；零售 entry {base}，追加 {2 * len(order)}")
    base, n = verify(order, tools, anmmap)
    print(f"verify: entry {n} = {base} + 2×{len(order)}；零售 spec/贴图逐项一致；cards.js 索引一致\n")
    print(f"{'NAME':<16}{'sprite_large':>13}{'sprite_small':>13}")
    for name, (lg, sm) in expected_sprites(order, base).items():
        print(f"{name:<16}{lg:>13}{sm:>13}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
