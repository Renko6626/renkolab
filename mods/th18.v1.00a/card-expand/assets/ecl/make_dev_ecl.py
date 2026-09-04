#!/usr/bin/env python3
"""开发辅助：把 st01 做成「近乎空壳」——进关就是 logo → 对话 → 一发一阶段的 boss → 关底商店。只进 _test patch。

    python3 make_dev_ecl.py            # → native/build/ecl/st01.ecl, st01bs.ecl

  st01.ecl   源文本就在仓库里：assets/ecl/st01.ecl.txt（真·空壳：只剩头部、main、LogoEnemy、MainBoss，零售敌机子程序一律不留），
             直接 thecl -c 编译。
  st01bs.ecl 满是 ZUN 的符卡脚本，不入库：现场反编译 local/th18.v1.00a/dat/st01bs.ecl，血量常数（lifeSet /
             setInterrupt 阈值 / lifeMarker）等比 ÷100（14100 → 141，阶段切换阈值 2100 → 21），再编回。thecl 往返在它上面字节一致，没改的部分不会走样。
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



LIFE_DIV = 100
BOSS_MONEY_DROP = 300   # boss 死时额外掉的金钱道具数（每个 +1 金）；道具池若不够就少掉，无害


def _scale(n: int) -> int:
    return max(1, n // LIFE_DIV) if n > 0 else n


def patch_boss(text):
    """血量常数等比 ÷LIFE_DIV，阈值顺序不变：lifeSet(N)、setInterrupt(槽, 血量, 超时, 子程序) 的血量、lifeMarker(槽, 血量, 色) 的血量。
    超时帧不动。只改 lifeSet 而不改阈值会让血条刻度 / 阶段切换乱掉（2026-09-04 实跑「符卡血量诡异」）。"""
    n = 0
    def f_life(m):
        nonlocal n; n += 1
        return f"lifeSet({_scale(int(m.group(1)))})"
    def f_int(m):
        nonlocal n; n += 1
        return f"setInterrupt({m.group(1)}, {_scale(int(m.group(2)))}, {m.group(3)}"
    def f_mark(m):
        nonlocal n; n += 1
        return f"lifeMarker({m.group(1)}, {_scale(int(float(m.group(2))))}.0f"
    text = re.sub(r"lifeSet\((\d+)\)", f_life, text)
    text = re.sub(r"setInterrupt\((-?\d+), (\d+), (-?\d+)", f_int, text)
    text = re.sub(r"lifeMarker\((-?\d+), ([0-9.]+)f", f_mark, text)
    if n == 0:
        raise SystemExit("st01bs.ecl 里没有血量相关指令")
    # boss 死时多掉金钱道具：BossDead 里零售 @BossItem(16, 10, 10)（16 = 卡道具，10 火力，10 金钱）之后再撒一批。
    # type 2 = 金钱道具，吃一个 MONEY += 1（05-shop-and-money §1）。dropArea 撒开一点免得叠在一处。
    anchor = "    @BossItem(16, 10, 10);\n"
    if anchor not in text:
        raise SystemExit("st01bs.ecl 的 BossDead 里找不到 @BossItem(16, 10, 10)")
    text = text.replace(anchor, anchor + f"    dropClear();\n    dropExtra(2, {BOSS_MONEY_DROP});\n    dropArea(320.0f, 160.0f);\n    dropItems();\n", 1)
    return text, n


def main():
    t = thecl()
    OUT.mkdir(parents=True, exist_ok=True)
    src = HERE / "st01.ecl.txt"
    run([t, "-c", VERSION, "-m", ECLMAP, src, OUT / "st01.ecl"])
    bs, n = patch_boss(decompile(t, "st01bs"))
    compile_(t, "st01bs", bs)
    print(f"ecl: st01.ecl（空壳，源 {src.relative_to(MOD)}）、st01bs.ecl（{n} 处血量常数 ÷{LIFE_DIV}，boss 死时 +{BOSS_MONEY_DROP} 金钱道具）→ {OUT.relative_to(MOD)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
