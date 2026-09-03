#!/usr/bin/env python3
"""把一张现成的卡图（任意尺寸/比例）裁切、等比缩放到 abcard.anm 的 256×320 / 64×80。

    python3 fit_card.py REVERSE reverse_card.png                 # 自动框出卡片（去白边），上下各修 3%，白底
    python3 fit_card.py NAME src.png --trim 0 --bg '#000000'     # 不修边、黑底
    python3 fit_card.py NAME src.png --no-detect                 # 不做去白边，整图直接放

步骤：① 去白边（非白像素的包围盒）② 上下各修 --trim 比例（比例太瘦时少留点白）③ 等比缩到
高 320 − 2·margin，居中贴到 --bg 底色的 256×320 上 ④ _min = 整图缩到 64×80。
"""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageChops

HERE = Path(__file__).resolve().parent
OUT = HERE / "cards"
MAX_W, MAX_H = 256, 320
MIN_W, MIN_H = 64, 80


def detect_card(im: Image.Image, white=235):
    """非白像素的包围盒（源图外围通常是纯白出血）。"""
    g = im.convert("L").point(lambda v: 0 if v >= white else 255)
    return g.getbbox() or (0, 0, im.width, im.height)


def fit(src: Path, trim: float, bg: str, detect: bool, margin: int) -> Image.Image:
    im = Image.open(src).convert("RGBA")
    if detect:
        im = im.crop(detect_card(im))
    if trim:
        t = int(im.height * trim)
        im = im.crop((0, t, im.width, im.height - t))
    h = MAX_H - 2 * margin
    w = round(im.width * h / im.height)
    if w > MAX_W - 2 * margin:            # 太宽就按宽度缩
        w = MAX_W - 2 * margin
        h = round(im.height * w / im.width)
    im = im.resize((w, h), Image.LANCZOS)
    canvas = Image.new("RGBA", (MAX_W, MAX_H), bg)
    canvas.alpha_composite(im, ((MAX_W - w) // 2, (MAX_H - h) // 2))
    return canvas


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("name")
    ap.add_argument("src", type=Path)
    ap.add_argument("--trim", type=float, default=0.03, help="上下各修掉的比例（默认 0.03）")
    ap.add_argument("--bg", default="#ffffff", help="底色（默认白）")
    ap.add_argument("--margin", type=int, default=8, help="上下留白像素（默认 8）")
    ap.add_argument("--no-detect", action="store_true", help="不做去白边")
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    big = fit(a.src, a.trim, a.bg, not a.no_detect, a.margin)
    big.save(out / f"{a.name}_max.png")
    big.resize((MIN_W, MIN_H), Image.LANCZOS).save(out / f"{a.name}_min.png")
    print(f"{a.name}: {a.name}_max.png {MAX_W}x{MAX_H} · {a.name}_min.png {MIN_W}x{MIN_H}  ← {a.src.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
