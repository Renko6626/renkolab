#!/usr/bin/env python3
"""给还没画图的卡生成占位卡图（花色 + 点数），尺寸符合 abcard.anm 的要求。

    python3 gen_placeholder.py                       # 内置表：黑桃 10/J/Q/K/A
    python3 gen_placeholder.py SPADE_7 ♠ 7           # 单张
    python3 gen_placeholder.py HEART_A ♥ A --color '#c0392b'

输出 cards/<NAME>_max.png（256×320）与 cards/<NAME>_min.png（64×80），RGBA。
只是占位——真图由写卡的人替换，尺寸不变即可。
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

DEFAULT = [  # NAME, 花色, 点数
    ("SPADE_10", "♠", "10"),
    ("SPADE_J", "♠", "J"),
    ("SPADE_Q", "♠", "Q"),
    ("SPADE_K", "♠", "K"),
    ("SPADE_A", "♠", "A"),
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


def draw_card(suit: str, rank: str, color: str) -> Image.Image:
    im = Image.new("RGBA", (MAX_W, MAX_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((4, 4, MAX_W - 5, MAX_H - 5), radius=22, fill=(24, 26, 34, 255),
                        outline=(230, 230, 235, 255), width=4)
    d.rounded_rectangle((16, 16, MAX_W - 17, MAX_H - 17), radius=14, outline=(120, 120, 130, 255), width=2)
    f_big, f_rank = font(150), font(44)
    d.text((MAX_W / 2, MAX_H / 2 + 6), suit, font=f_big, fill=color, anchor="mm")
    d.text((26, 22), rank, font=f_rank, fill=(240, 240, 245, 255), anchor="la")
    d.text((MAX_W - 26, MAX_H - 22), rank, font=f_rank, fill=(240, 240, 245, 255), anchor="rd")
    return im


def emit(name: str, suit: str, rank: str, color: str, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    big = draw_card(suit, rank, color)
    big.save(out / f"{name}_max.png")
    big.resize((MIN_W, MIN_H), Image.LANCZOS).save(out / f"{name}_min.png")
    print(f"{name}: {name}_max.png {MAX_W}x{MAX_H} · {name}_min.png {MIN_W}x{MIN_H}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("name", nargs="?")
    ap.add_argument("suit", nargs="?")
    ap.add_argument("rank", nargs="?")
    ap.add_argument("--color", default="#e8e8ee", help="花色颜色（默认近白）")
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    out = Path(a.out)
    if a.name:
        if not (a.suit and a.rank):
            ap.error("单张要给 NAME 花色 点数 三个参数")
        emit(a.name, a.suit, a.rank, a.color, out)
    else:
        for name, suit, rank in DEFAULT:
            emit(name, suit, rank, a.color, out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
