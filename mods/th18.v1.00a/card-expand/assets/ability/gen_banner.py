#!/usr/bin/env python3
"""生成「ROYAL FLUSH」横幅贴图：金色 + 金属光泽 + 黑色描边 + 阴影，512×128 RGBA（ability.anm 追加用）。

    python3 gen_banner.py                       # → banner/ROYAL_FLUSH.png
    python3 gen_banner.py "FULL HOUSE" --out banner/FULL_HOUSE.png

做法：4 倍超采样画文字蒙版 → 竖向金色渐变（亮金-深金-高光带-暗金）+ 一条斜向高光 → 按蒙版贴进画布 →
黑描边（stroke）与右下阴影 → 缩到 512×128（LANCZOS）。字体走 fc-match，优先 DejaVu Sans Bold / Noto Sans Bold。
"""
import argparse
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
W, H = 512, 128
SS = 4                                  # 超采样倍数


def font(size, prefer=("DejaVu Sans:bold", "Noto Sans:bold", "Noto Serif CJK SC:bold")):
    for name in prefer:
        try:
            path = subprocess.run(["fc-match", "-f", "%{file}", name], capture_output=True, text=True, check=True).stdout.strip()
            if path:
                return ImageFont.truetype(path, size)
        except Exception:  # noqa: BLE001
            continue
    return ImageFont.load_default()


def gold_gradient(w, h):
    """竖向金属渐变：顶亮金 → 深金 → 中部高光带 → 底暗金。"""
    stops = [(0.00, (255, 246, 190)), (0.30, (255, 205, 60)), (0.48, (176, 120, 10)),
             (0.55, (255, 236, 150)), (0.72, (232, 172, 30)), (1.00, (120, 70, 5))]
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        t = y / max(1, h - 1)
        for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
            if t0 <= t <= t1:
                k = (t - t0) / (t1 - t0) if t1 > t0 else 0
                c = tuple(int(a + (b - a) * k) for a, b in zip(c0, c1))
                break
        for x in range(w):
            px[x, y] = c
    # 斜向高光带（金属反光）
    hl = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(hl)
    band = w // 6
    for i in range(-h, w, 1):
        pass
    d.polygon([(w * 0.55, 0), (w * 0.55 + band, 0), (w * 0.35 + band, h), (w * 0.35, h)], fill=140)
    hl = hl.filter(ImageFilter.GaussianBlur(w // 40))
    white = Image.new("RGB", (w, h), (255, 255, 240))
    return Image.composite(white, img, hl).convert("RGBA")


def render(text: str) -> Image.Image:
    w, h = W * SS, H * SS
    # 字号：让文字宽度约占 92%
    size = 64 * SS
    f = font(size)
    while True:
        bbox = ImageDraw.Draw(Image.new("L", (1, 1))).textbbox((0, 0), text, font=f, stroke_width=0)
        tw = bbox[2] - bbox[0]
        if tw <= w * 0.90 or size <= 8 * SS:
            break
        size -= 2 * SS
        f = font(size)
    stroke = 5 * SS
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    # 阴影
    shadow = Image.new("L", (w, h), 0)
    ImageDraw.Draw(shadow).text((w / 2 + 3 * SS, h / 2 + 4 * SS), text, font=f, fill=200, anchor="mm", stroke_width=stroke, stroke_fill=200)
    shadow = shadow.filter(ImageFilter.GaussianBlur(3 * SS))
    canvas.alpha_composite(Image.merge("RGBA", (Image.new("L", (w, h), 0),) * 3 + (shadow,)))
    # 黑描边
    outline = Image.new("L", (w, h), 0)
    ImageDraw.Draw(outline).text((w / 2, h / 2), text, font=f, fill=255, anchor="mm", stroke_width=stroke, stroke_fill=255)
    canvas.alpha_composite(Image.merge("RGBA", (Image.new("L", (w, h), 10),) * 3 + (outline,)))
    # 金色字面
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).text((w / 2, h / 2), text, font=f, fill=255, anchor="mm")
    gold = gold_gradient(w, h)
    gold.putalpha(mask)
    canvas.alpha_composite(gold)
    # 顶部细高光线（贴着描边内侧）
    return canvas.resize((W, H), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("text", nargs="?", default="ROYAL FLUSH")
    ap.add_argument("--out", default=str(HERE / "banner" / "ROYAL_FLUSH.png"))
    a = ap.parse_args()
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    render(a.text).save(out)
    print(f"{out.relative_to(HERE.parents[0]) if out.is_relative_to(HERE.parents[0]) else out}: {W}x{H}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
