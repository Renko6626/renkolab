#!/usr/bin/env python3
"""开发辅助：把 st01 做成「近乎空壳」——进关就是 logo → 对话 → 一发一阶段的 boss → 关底商店。只进 _test patch。

    python3 make_dev_ecl.py            # → native/build/ecl/st01.ecl, st01bs.ecl

  st01.ecl   源文本就在仓库里：assets/ecl/st01.ecl.txt（真·空壳：只剩头部、main、LogoEnemy、MainBoss，零售敌机子程序一律不留），
             直接 thecl -c 编译。
  st01bs.ecl 满是 ZUN 的符卡脚本，不入库：现场反编译 local/th18.v1.00a/dat/st01bs.ecl，所有 lifeSet(N) → lifeSet(1)
             （boss 每个阶段一发就过），再编回。thecl 往返在它上面字节一致，没改的部分不会走样。
"""
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MOD = HERE.parents[1]
REPO = MOD.parents[2]
sys.path.insert(0, str(REPO / "tooling" / "thtk"))
from unpack import find_tools  # noqa: E402

VERSION = "18"
DAT = REPO / "local" / "th18.v1.00a" / "dat"
OUT = MOD / "native" / "build" / "ecl"
ECLMAP = REPO / "local" / "vendor" / "eclmap" / "eclmap" / "th18.eclm"



def thecl():
    p = REPO / "local" / "vendor" / "thtk" / "build" / "thecl" / "thecl"
    if not p.is_file():
        raise SystemExit("没有 thecl：bash tooling/thtk/build.sh（会连 thecl 一起编）")
    if not ECLMAP.is_file():
        raise SystemExit("没有 th18 eclmap：git clone https://github.com/Priw8/eclmap local/vendor/eclmap")
    return p


def run(args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0 or r.stderr.strip():
        raise SystemExit(f"{' '.join(map(str, args))} 失败：\n{r.stderr or r.stdout}")


def decompile(t, name):
    src = DAT / f"{name}.ecl"
    if not src.is_file():
        raise SystemExit(f"没有 {src}：先 python3 tooling/thtk/unpack.py th18.v1.00a")
    txt = OUT / f"{name}.retail.txt"
    run([t, "-d", VERSION, "-m", ECLMAP, src, txt])
    return txt.read_text(encoding="utf-8", errors="surrogateescape")   # 字符串是 Shift-JIS，按字节原样往返


def compile_(t, name, text):
    txt = OUT / f"{name}.dev.txt"
    txt.write_text(text, encoding="utf-8", errors="surrogateescape")
    run([t, "-c", VERSION, "-m", ECLMAP, txt, OUT / f"{name}.ecl"])



def patch_boss(text):
    text2, n = re.subn(r"lifeSet\(\d+\)", "lifeSet(1)", text)
    if n == 0:
        raise SystemExit("st01bs.ecl 里没有 lifeSet(N)")
    return text2, n


def main():
    t = thecl()
    OUT.mkdir(parents=True, exist_ok=True)
    src = HERE / "st01.ecl.txt"
    run([t, "-c", VERSION, "-m", ECLMAP, src, OUT / "st01.ecl"])
    bs, n = patch_boss(decompile(t, "st01bs"))
    compile_(t, "st01bs", bs)
    print(f"ecl: st01.ecl（空壳，源 {src.relative_to(MOD)}）、st01bs.ecl（{n} 处 lifeSet → 1）→ {OUT.relative_to(MOD)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
