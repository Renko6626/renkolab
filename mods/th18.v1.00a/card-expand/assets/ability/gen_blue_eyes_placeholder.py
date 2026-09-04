#!/usr/bin/env python3
"""青眼白龙占位贴图（正式图由用户出）：

    python3 gen_blue_eyes_placeholder.py

  blue_eyes/DRAGON.png  128×128 RGBA：淡蓝白色的龙形剪影（身体椭圆 + 两翼三角 + 蓝眼），透明底
  blue_eyes/BEAM.png    32×512  RGBA：竖向白→淡蓝光柱，两侧渐透明，透明底
"""
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
OUT = HERE / "blue_eyes"


def dragon() -> Image.Image:
    im = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    body = (235, 245, 255, 255)
    edge = (120, 170, 230, 255)
    d.polygon([(64, 40), (8, 20), (30, 70)], fill=body, outline=edge)          # 左翼
    d.polygon([(64, 40), (120, 20), (98, 70)], fill=body, outline=edge)        # 右翼
    d.ellipse((36, 44, 92, 108), fill=body, outline=edge, width=2)             # 身体
    d.ellipse((48, 20, 80, 56), fill=body, outline=edge, width=2)              # 头
    d.polygon([(64, 56), (54, 76), (74, 76)], fill=edge)                        # 颈纹
    d.ellipse((56, 32, 62, 38), fill=(40, 120, 255, 255))                       # 左眼
    d.ellipse((66, 32, 72, 38), fill=(40, 120, 255, 255))                       # 右眼
    d.polygon([(64, 108), (58, 124), (70, 124)], fill=body, outline=edge)       # 尾
    return im


def beam() -> Image.Image:
    w, h = 32, 512
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = im.load()
    for x in range(w):
        t = abs(x - (w - 1) / 2) / ((w - 1) / 2)          # 0 中心 → 1 边缘
        a = int(255 * (1.0 - t) ** 1.5)
        for y in range(h):
            fade = 1.0 if y > 48 else y / 48.0             # 顶端 48 px 渐隐（远端）
            px[x, y] = (220, 240, 255, int(a * fade))
    return im


def main():
    OUT.mkdir(exist_ok=True)
    dragon().save(OUT / "DRAGON.png")
    beam().save(OUT / "BEAM.png")
    print(f"wrote {OUT / 'DRAGON.png'} (128x128), {OUT / 'BEAM.png'} (32x512)")


if __name__ == "__main__":
    main()
