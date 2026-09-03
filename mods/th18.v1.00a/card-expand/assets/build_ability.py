#!/usr/bin/env python3
"""往零售 ability.anm 追加贴图 entry 与特效脚本，重编到 native/build/ability.anm，并生成 native/anm_ids.h。

    python3 build_ability.py                # 构建 + 自检 + 写 anm_ids.h
    python3 build_ability.py --verify-only  # 只自检已有的 build/ability.anm

输入：
    ability/entries/ORDER.txt     一行 `NAME  源图路径(相对 assets/)`；只追加不重排。
                                  第 k 行 → entry (7+k)、sprite (109+k)（数字由零售文件算出，不写死）
    ability/scripts/NN_name.anm.txt  一个文件一个脚本，NN 从 68 起连续；正文可用 @NAME 引用 ORDER 里的 sprite 号
输出：
    native/build/ability.anm、native/anm_ids.h（CE_ANM_ABILITY_SPRITE_<NAME> / CE_ANM_ABILITY_SCRIPT_<name>）

贴图 entry 字段照抄 abcard 的 BLANK_max（256×512 贴图、THTX 256×320、format 1）——源图必须是 256×320。
"""
import argparse
import re
import sys
from pathlib import Path

import anmlib as L

HERE, MOD = L.HERE, L.MOD
ENTRIES = HERE / "ability" / "entries" / "ORDER.txt"
SCRIPTS = HERE / "ability" / "scripts"
TEX = L.BUILD / "tex-ability"
OUT_ANM = L.BUILD / "ability.anm"
IDS_H = MOD / "native" / "anm_ids.h"
TEMPLATE = ("abcard", "ability/BLANK_max.png")
_FILE = re.compile(r"^(\d+)_([A-Za-z_][A-Za-z0-9_]*)\.anm\.txt$")


def plan(retail_text: str):
    """→ (entries=[(name, src, entry_idx, sprite_idx)], scripts=[(name, path, script_idx)])。"""
    n_entry = len(L.parse_entries(retail_text))
    n_script = len(L.parse_scripts(retail_text))
    sprite0 = L.max_sprite_id(retail_text) + 1
    entries = [(r[0], HERE / r[1], n_entry + k, sprite0 + k) for k, r in enumerate(L.read_order(ENTRIES))]
    scripts = []
    for k, p in enumerate(sorted(SCRIPTS.glob("*.anm.txt"))):
        m = _FILE.match(p.name)
        if not m:
            raise SystemExit(f"{p.name}：文件名要像 68_reverse_flash.anm.txt")
        want = n_script + k
        if int(m.group(1)) != want:
            raise SystemExit(f"{p.name}：编号应为 {want}（零售 {n_script} 个脚本，按文件名顺序连续追加）")
        scripts.append((m.group(2), p, want))
    return entries, scripts


def write_ids_h(entries, scripts):
    lines = ["/* 由 assets/build_ability.py 生成 —— ability.anm 里追加的 sprite / 脚本号。别手改。 */",
             "#pragma once", ""]
    for name, _, eidx, sidx in entries:
        lines.append(f"#define CE_ANM_ABILITY_SPRITE_{name.upper():<20} {sidx:>4}   /* entry{eidx} */")
    for name, _, idx in scripts:
        lines.append(f"#define CE_ANM_ABILITY_SCRIPT_{name.upper():<20} {idx:>4}")
    IDS_H.write_text("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--verify-only", action="store_true")
    a = ap.parse_args()
    th, td, mapdir = L.find_tools()
    tools, anmmap = (th, td), mapdir / "v8.anmm"
    retail_dir, retail_text = L.retail("ability")
    retail_entries = L.parse_entries(retail_text)
    tpl = {e["name"]: e for e in L.parse_entries(L.retail(TEMPLATE[0])[1])}[TEMPLATE[1]]
    entries, scripts = plan(retail_text)
    mapping = {name: f"sprite{sidx}" for name, _, _, sidx in entries}

    if not a.verify_only:
        from PIL import Image
        want = (int(tpl["fields"]["THTXWidth"]), int(tpl["fields"]["THTXHeight"]))
        L.fresh_dir(TEX)
        L.link_retail_textures(TEX, retail_dir, retail_entries)
        (TEX / "ability").mkdir(exist_ok=True)
        blocks = []
        for name, src, eidx, sidx in entries:
            if not src.is_file():
                raise SystemExit(f"缺 {src}")
            im = Image.open(src).convert("RGBA")
            if im.size != want:
                raise SystemExit(f"{src.name} 是 {im.size}，要 {want}")
            im.save(TEX / "ability" / f"{name}.png")
            blocks.append(L.make_entry(tpl, eidx, f"ability/{name}.png", sprite_idx=sidx))
        text = L.insert_entries(retail_text, blocks) if blocks else retail_text
        sblocks = []
        for name, p, idx in scripts:
            body = L.substitute(p.read_text(), mapping)
            if not body.lstrip().startswith(f"script script{idx} {{"):
                raise SystemExit(f"{p.name}：开头应为 `script script{idx} {{`")
            sblocks.append(body)
        if sblocks:
            text = L.append_scripts(text, sblocks)
        L.compile_anm(text, TEX, OUT_ANM, tools, anmmap)
        print(f"build: {OUT_ANM.relative_to(MOD)}（{OUT_ANM.stat().st_size:,} B）；零售 entry {len(retail_entries)} + {len(entries)}，"
              f"script {len(L.parse_scripts(retail_text))} + {len(scripts)}")

    _, n_e, n_s = L.verify_rebuilt(OUT_ANM, retail_text, retail_dir, tools, anmmap)
    if len(n_e) != len(retail_entries) + len(entries) or len(n_s) != len(L.parse_scripts(retail_text)) + len(scripts):
        raise SystemExit(f"entry {len(n_e)} / script {len(n_s)}，与计划不符")
    for name, _, eidx, sidx in entries:
        e = n_e[eidx]
        if e["name"] != f"ability/{name}.png" or e["fields"] != tpl["fields"] or e["sprite"] != tpl["sprite"] \
                or f"sprite{sidx}:" not in e["block"]:
            raise SystemExit(f"新 entry{eidx}（{name}）字段与模板不一致")
    write_ids_h(entries, scripts)
    print(f"verify: entry {len(n_e)}、script {len(n_s)}；零售 spec/贴图逐项一致；写 {IDS_H.relative_to(MOD)}\n")
    for name, _, eidx, sidx in entries:
        print(f"  entry{eidx:<4} sprite{sidx:<5} {name}")
    for name, _, idx in scripts:
        print(f"  script{idx:<12} {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
