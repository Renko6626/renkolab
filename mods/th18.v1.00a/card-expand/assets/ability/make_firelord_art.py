#!/usr/bin/env python3
"""炎魔之王拉格纳罗斯（id 72）的场上贴图：

    python3 make_firelord_art.py

  firelord/RAGNAROS.png  256×256 RGBA：从 _src/FIRELORD_TOPDOWN.png（用户原创，白底正面像，1189×1323）抠掉白底，
                         等比缩到 256 高、居中（script91 再 scale 0.5 → 场上约 128 px 高）
  firelord/FIREBALL.png  64×64 RGBA：程序生成的火球——白芯 → 黄 → 橙 → 红，边缘带确定性噪声的火舌；
                         火球本体（script92）、拖尾（script93）都用它
  firelord/BLAST.png     128×128 RGBA：爆炸——内圈黄白闪光 + 外圈橙红光环（script94 从 0.3 放大到 1.5 淡出）

抠白底：从四角泛洪（阈值 24）得到背景掩码 → 掩码外扩 2 px 的环里按「离白多远」（255 − min(r,g,b)）做 alpha 斜坡，
火焰内部的亮黄（不与背景连通）保持不透明。程序贴图用固定种子，重跑逐字节一致。
"""
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
OUT = HERE / "firelord"
SRC = OUT / "_src" / "FIRELORD_TOPDOWN.png"
SENTINEL = (255, 0, 255)
SEED = 0x5E1F


def key_white(im: Image.Image) -> Image.Image:
    rgb = im.convert("RGB")
    w, h = rgb.size
    flood = rgb.copy()
    for seed in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        ImageDraw.floodfill(flood, seed, SENTINEL, thresh=24)
    fpx = flood.load()
    mask = Image.new("L", (w, h), 0)              # 255 = 背景
    mpx = mask.load()
    for y in range(h):
        for x in range(w):
            if fpx[x, y] == SENTINEL:
                mpx[x, y] = 255
    ring = mask.filter(ImageFilter.MaxFilter(5))   # 背景外扩 2 px：边缘抗锯齿像素在这圈里
    rpx = ring.load()
    px = rgb.load()
    out = Image.new("RGBA", (w, h))
    opx = out.load()
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            if mpx[x, y]:
                a = 0
            elif rpx[x, y]:
                a = max(0, min(255, (255 - min(r, g, b) - 8) * 255 // 48))
            else:
                a = 255
            opx[x, y] = (r, g, b, a)
    return out


def body() -> Image.Image:
    im = key_white(Image.open(SRC))
    im = im.crop(im.getbbox())
    scale = 256 / im.height
    im = im.resize((max(1, round(im.width * scale)), 256), Image.LANCZOS)
    canvas = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    canvas.paste(im, ((256 - im.width) // 2, 0), im)
    return canvas


def _lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _fire_color(t):
    """t ∈ [0,1]：0 = 白芯，1 = 暗红边。"""
    stops = [(0.0, (255, 255, 240)), (0.18, (255, 235, 120)), (0.45, (255, 150, 30)),
             (0.75, (230, 60, 10)), (1.0, (120, 10, 0))]
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1:
            return _lerp(c0, c1, (t - t0) / (t1 - t0))
    return stops[-1][1]


def _noise_table(rng, n=64):
    return [rng.random() for _ in range(n)]


def fireball(size=64) -> Image.Image:
    rng = random.Random(SEED)
    noise = _noise_table(rng)
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = im.load()
    c = (size - 1) / 2
    r_max = size * 0.47
    for y in range(size):
        for x in range(size):
            dx, dy = x - c, y - c
            d = math.hypot(dx, dy)
            ang = math.atan2(dy, dx)
            k = int(((ang + math.pi) / (2 * math.pi)) * len(noise)) % len(noise)
            edge = r_max * (0.82 + 0.18 * noise[k])      # 边缘火舌：半径按角度抖动
            t = d / edge
            if t >= 1.0:
                continue
            a = (1.0 - t) ** 1.6
            a = min(1.0, a * 1.25)
            col = _fire_color(min(1.0, t * 1.05))
            px[x, y] = (*col, round(a * 255))
    return im


def blast(size=128) -> Image.Image:
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = im.load()
    c = (size - 1) / 2
    ring_r, ring_w = size * 0.36, size * 0.07
    core_r = size * 0.16
    for y in range(size):
        for x in range(size):
            d = math.hypot(x - c, y - c)
            # 外圈光环
            ring = math.exp(-((d - ring_r) / ring_w) ** 2)
            # 内圈闪光
            core = max(0.0, 1.0 - d / core_r) ** 1.2 if d < core_r else 0.0
            a = min(1.0, ring * 0.95 + core)
            if a < 0.01:
                continue
            t = 0.15 if core > ring else min(1.0, 0.45 + (d - ring_r) / (size * 0.14))
            col = _fire_color(max(0.0, min(1.0, t)))
            px[x, y] = (*col, round(a * 255))
    return im


def main():
    OUT.mkdir(exist_ok=True)
    b = body()
    b.save(OUT / "RAGNAROS.png")
    print(f"wrote {OUT / 'RAGNAROS.png'} {b.size} (bbox {b.getbbox()})")
    f = fireball()
    f.save(OUT / "FIREBALL.png")
    print(f"wrote {OUT / 'FIREBALL.png'} {f.size}")
    x = blast()
    x.save(OUT / "BLAST.png")
    print(f"wrote {OUT / 'BLAST.png'} {x.size}")


if __name__ == "__main__":
    main()
