#!/usr/bin/env python3
"""破损核心（id 71）的场上贴图与卡图画面。用户原创两张 + 程序生成一张（固定种子，重跑逐字节一致）。

    python3 make_broken_core_art.py

  broken_core/CORE.png   128×128  场上的电球子机：用户原创 `_src/LightningOrb.png`（70×70 黄绿球），
                                  按 alpha 包围盒裁切、等比放大到 112 px、居中
  broken_core/BOLT.png   256×64   电球 → 敌人之间那道电弧，程序生成：黄白色闪电链，画成**朝 +x 铺满整幅**，
                                  C 在开火那帧把 VM 的旋转设成瞄准角、scale.x 设成 距离/256
  _src/BROKEN_CORE_face.png 512×640  卡图画面：用户原创 `cards/_src/BROKEN_CORE.png`（156×156 青色裂核，透明底）
                                  按 alpha 包围盒裁切、放大到画面宽的 78％、居中铺在**白底**上 → 再跑
      python3 ../fit_card.py BROKEN_CORE ability/broken_core/_src/BROKEN_CORE_face.png \
              --no-detect --trim 0 --margin 0 --bg '#ffffff'

闪电是**瞬发的**，不是飞行物：伤害是一个小定点伤害源钉在目标上（`0x45dfa0`，24×24、寿命 2 帧），
BOLT 只是特效——横向拉到「电球 → 敌人」那么长。所以它要**耐拉伸**：主干贯穿整幅、
只在左端（电球那头）收一点，右端不淡出（那头顶在敌人身上）。
"""
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

HERE = Path(__file__).resolve().parent
OUT = HERE / "broken_core"
SRC = OUT / "_src"
SEED = 0x1971  # 破损核心 = id 71


def to_image(rgb: np.ndarray, a: np.ndarray) -> Image.Image:
    """rgb: (h, w, 3) 0..1，a: (h, w) 0..1 → RGBA8。"""
    arr = np.concatenate([rgb, a[..., None]], axis=2)
    return Image.fromarray(np.clip(arr * 255.0 + 0.5, 0, 255).astype(np.uint8), "RGBA")


def radial(h: int, w: int, cx: float, cy: float):
    y, x = np.mgrid[0:h, 0:w].astype(np.float64)
    return np.hypot(x - cx, y - cy)


def polyline_mask(h: int, w: int, pts, width: float) -> np.ndarray:
    """折线的距离场 → 0..1 掩码（1 = 线心）。纯 numpy，逐段算点到线段距离。"""
    y, x = np.mgrid[0:h, 0:w].astype(np.float64)
    best = np.full((h, w), 1e9)
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        dx, dy = x1 - x0, y1 - y0
        seg = dx * dx + dy * dy
        t = np.clip(((x - x0) * dx + (y - y0) * dy) / max(seg, 1e-9), 0.0, 1.0)
        best = np.minimum(best, np.hypot(x - (x0 + t * dx), y - (y0 + t * dy)))
    return np.clip(1.0 - best / max(width, 1e-9), 0.0, 1.0)


def jagged(rng, x0, y0, x1, y1, segments, jitter):
    """两点之间的锯齿折线：等分后每个中间点沿法线抖动。"""
    pts = []
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / length, dx / length
    for i in range(segments + 1):
        t = i / segments
        j = 0.0 if i in (0, segments) else rng.uniform(-jitter, jitter)
        pts.append((x0 + dx * t + nx * j, y0 + dy * t + ny * j))
    return pts


def glow(mask: np.ndarray, radius: float) -> np.ndarray:
    im = Image.fromarray((np.clip(mask, 0, 1) * 255).astype(np.uint8), "L")
    return np.asarray(im.filter(ImageFilter.GaussianBlur(radius)), dtype=np.float64) / 255.0


# ---------------------------------------------------------------- 电球（用户原创）

ORB_SRC = SRC / "LightningOrb.png"
CARD_SRC = HERE.parent / "cards" / "_src" / "BROKEN_CORE.png"


def fit_center(src: Path, canvas: tuple, frac: float, bg=(0, 0, 0, 0)) -> Image.Image:
    """按 alpha 包围盒裁切 → 等比缩放到「较长边 = 画布对应边 × frac」→ 居中铺在 bg 上。"""
    im = Image.open(src).convert("RGBA")
    im = im.crop(im.getbbox())
    cw, ch = canvas
    scale = min(cw * frac / im.width, ch * frac / im.height)
    im = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.LANCZOS)
    out = Image.new("RGBA", canvas, bg)
    out.alpha_composite(im, ((cw - im.width) // 2, (ch - im.height) // 2))
    return out


def orb(size=128) -> Image.Image:
    return fit_center(ORB_SRC, (size, size), 112 / 128)


# ---------------------------------------------------------------- 电弧（程序生成）

def bolt(w=256, h=64) -> Image.Image:
    """黄白色闪电链：一条主干 + 一条错开半拍的副干互相缠绕（链的感觉），再挂几条短分叉。"""
    rng = np.random.default_rng(SEED + 1)
    main = jagged(rng, 0.0, h / 2, float(w), h / 2, 13, h * 0.24)            # 主干贯穿整幅（要耐横向拉伸）
    twin = [(x, h - y) for x, y in main]                                    # 副干：主干上下镜像 → 两股交缠
    twin = [(x, y + rng.uniform(-3, 3)) for x, y in twin]
    core = np.maximum(polyline_mask(h, w, main, 1.9), polyline_mask(h, w, twin, 1.3) * 0.8)
    branches = np.zeros((h, w))
    for i in (2, 5, 8, 11):                                                 # 四条短分叉
        bx, by = main[i]
        branches = np.maximum(branches, polyline_mask(
            h, w, jagged(rng, bx, by, bx + rng.uniform(12, 26), by + rng.uniform(-18, 18), 3, 5.0), 1.1))
    line = np.clip(core + branches * 0.6, 0.0, 1.0)
    inten = np.clip(line + glow(line, 2.0) * 1.1 + glow(line, 7.0) * 0.85, 0.0, 1.5)

    x = np.mgrid[0:h, 0:w][1].astype(np.float64)
    inten *= np.clip(x / 12.0, 0.0, 1.0)                                    # 只在左端（电球那头）收一点

    hot = np.clip((inten - 0.5) / 0.5, 0.0, 1.0)                            # 线心白、辉光黄
    rgb = np.stack([np.full_like(hot, 1.0),
                    0.86 + 0.14 * hot,
                    0.30 + 0.70 * hot], axis=2)
    return to_image(rgb, np.clip(inten, 0.0, 1.0))


# ---------------------------------------------------------------- 卡图画面

def card_face(w=512, h=640) -> Image.Image:
    """用户原创裂核铺白底：alpha 包围盒裁切 → 放大到画面宽的 78％ → 居中。原图自带的柔和投影落在白底上变成浅灰，保留。"""
    return fit_center(CARD_SRC, (w, h), 0.78, bg=(255, 255, 255, 255))


def main():
    OUT.mkdir(exist_ok=True)
    SRC.mkdir(exist_ok=True)
    for path, im in ((OUT / "CORE.png", orb()),
                     (OUT / "BOLT.png", bolt()),
                     (SRC / "BROKEN_CORE_face.png", card_face())):
        im.save(path)
        print(f"wrote {path.relative_to(HERE.parent)} {im.size}")


if __name__ == "__main__":
    main()
