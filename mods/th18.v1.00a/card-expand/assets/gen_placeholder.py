#!/usr/bin/env python3
"""给还没画图的卡生成简洁卡图（白底黑图：花色 + 点数，或一张图标），尺寸符合 abcard.anm 的要求。

    python3 gen_placeholder.py                          # 内置表：黑桃 10/J/Q/K/A
    python3 gen_placeholder.py SPADE_7 --suit ♠ --rank 7 # 单张：花色 + 点数
    python3 gen_placeholder.py NAME --image icon.png    # 单张：居中放一张图标（透明底）

现成的整张卡图（如 UNO 反转牌）不走这里，用 fit_card.py 裁切缩放。

输出 cards/<NAME>_max.png（256×320）与 cards/<NAME>_min.png（64×80），RGBA。
"""
import argparse
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
OUT = HERE / "cards"
MAX_W, MAX_H = 256, 320
MIN_W, MIN_H = 64, 80

BG = (246, 246, 244, 255)
INK = (20, 20, 24, 255)
FRAME = (40, 40, 46, 255)

DEFAULT = [  # NAME, kwargs
    ("SPADE_10", dict(suit="♠", rank="10")),
    ("SPADE_J", dict(suit="♠", rank="J")),
    ("SPADE_Q", dict(suit="♠", rank="Q")),
    ("SPADE_K", dict(suit="♠", rank="K")),
    ("SPADE_A", dict(suit="♠", rank="A")),
]


def font(size: int, prefer=("Noto Serif CJK SC:bold", "DejaVu Sans:bold")):
    for name in prefer:
        try:
            path = subprocess.run(["fc-match", "-f", "%{file}", name],
                                  capture_output=True, text=True, check=True).stdout.strip()
            if path:
                return ImageFont.truetype(path, size)
        except Exception:  # noqa: BLE001 —— 没有 fc-match 或字体，退回默认
            continue
    return ImageFont.load_default()


def draw_card(suit=None, rank=None, image=None) -> Image.Image:
    im = Image.new("RGBA", (MAX_W, MAX_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((4, 4, MAX_W - 5, MAX_H - 5), radius=22, fill=BG, outline=FRAME, width=4)
    d.rounded_rectangle((16, 16, MAX_W - 17, MAX_H - 17), radius=14, outline=(170, 170, 176, 255), width=2)
    if image:
        icon = Image.open(image).convert("RGBA")
        icon.thumbnail((176, 176), Image.LANCZOS)
        im.alpha_composite(icon, ((MAX_W - icon.width) // 2, (MAX_H - icon.height) // 2))
    elif suit:
        d.text((MAX_W / 2, MAX_H / 2 + 6), suit, font=font(150), fill=INK, anchor="mm")
    if rank:
        f_rank = font(44)
        d.text((26, 22), rank, font=f_rank, fill=INK, anchor="la")
        d.text((MAX_W - 26, MAX_H - 22), rank, font=f_rank, fill=INK, anchor="rd")
    return im


def emit(name: str, out: Path, **kw):
    out.mkdir(parents=True, exist_ok=True)
    big = draw_card(**kw)
    big.save(out / f"{name}_max.png")
    big.resize((MIN_W, MIN_H), Image.LANCZOS).save(out / f"{name}_min.png")
    print(f"{name}: {name}_max.png {MAX_W}x{MAX_H} · {name}_min.png {MIN_W}x{MIN_H}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("name", nargs="?")
    ap.add_argument("--suit", help="花色字符，如 ♠")
    ap.add_argument("--rank", help="点数，如 10 / J")
    ap.add_argument("--image", type=Path, help="居中放的图标 PNG（透明底，黑图）")
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    out = Path(a.out)
    if a.name:
        if not (a.suit or a.image):
            ap.error("单张要给 --suit（配 --rank）或 --image")
        emit(a.name, out, suit=a.suit, rank=a.rank, image=a.image)
    else:
        for name, kw in DEFAULT:
            emit(name, out, **kw)
    return 0


if __name__ == "__main__":
    sys.exit(main())
