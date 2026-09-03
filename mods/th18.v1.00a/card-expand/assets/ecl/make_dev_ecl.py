#!/usr/bin/env python3
"""开发辅助：把 st01 做成「近乎空壳」——进关就是 logo → 对话 → 一发一阶段的 boss → 关底商店。只进 _test patch。

    python3 make_dev_ecl.py            # → native/build/ecl/st01.ecl, st01bs.ecl

零售 ECL 是 ZUN 的内容，仓库里只放这份变换脚本：现场用 thecl 反编译 local/th18.v1.00a/dat/ 的原文件，
做文本替换，再编回去。改动：
  st01.ecl   main：删掉 @MainFront() → 道中 boss → @MainLatter() 那一段（道中全部），只留 logo、短 wait、对话、boss
  st01bs.ecl 所有 lifeSet(N) → lifeSet(1)：boss 每个阶段一发就过
thecl 往返（-d 再 -c）在这两份文件上字节一致，所以没改的部分不会走样。
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

MAIN_CUT_BEGIN = "    @MainFront();\n"
MAIN_CUT_END = "    wait(200);\n"


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


def patch_main(text):
    m = re.search(r"^void main\(\)\n\{\n.*?^\}\n", text, re.S | re.M)
    if not m:
        raise SystemExit("st01.ecl 里找不到 main()")
    body = m.group(0)
    a, b = body.find(MAIN_CUT_BEGIN), body.find(MAIN_CUT_END)
    if a < 0 or b < a:
        raise SystemExit("st01 main 的道中段落长得和预期不一样（找不到 @MainFront() … wait(200);）")
    body2 = body[:a] + "    wait(30);\n" + body[b + len(MAIN_CUT_END):]
    return text.replace(body, body2, 1)


def patch_boss(text):
    text2, n = re.subn(r"lifeSet\(\d+\)", "lifeSet(1)", text)
    if n == 0:
        raise SystemExit("st01bs.ecl 里没有 lifeSet(N)")
    return text2, n


def main():
    t = thecl()
    OUT.mkdir(parents=True, exist_ok=True)
    st01 = patch_main(decompile(t, "st01"))
    compile_(t, "st01", st01)
    bs, n = patch_boss(decompile(t, "st01bs"))
    compile_(t, "st01bs", bs)
    print(f"ecl: st01.ecl（道中删除）、st01bs.ecl（{n} 处 lifeSet → 1）→ {OUT.relative_to(MOD)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
