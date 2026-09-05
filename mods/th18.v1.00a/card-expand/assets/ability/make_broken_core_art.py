#!/usr/bin/env python3
"""破损核心（id 71）的三张图，全部程序生成（确定性：固定种子，重跑逐字节一致）。

    python3 make_broken_core_art.py

  broken_core/CORE.png   128×128  场上的电球子机（加色混合：亮 = 光）
  broken_core/BOLT.png   256×64   电球 → 敌人之间那道弧。画成**朝 +x 铺满整幅**，C 在开火那帧
                                  把 VM 的旋转设成瞄准角、scale.x 设成 距离/256，于是它正好连住两点
  _src/BROKEN_CORE_face.png 512×640  卡图画面的源图 → 再跑
      python3 ../fit_card.py BROKEN_CORE ability/broken_core/_src/BROKEN_CORE_face.png \
              --no-detect --trim 0 --margin 0 --bg '#05070f'

闪电是**瞬发的**，不是飞行物：伤害是一个小定点伤害源钉在目标上（`0x45dfa0`，24×24、寿命 2 帧），
这张贴图只是特效——横向拉到「电球 → 敌人」那么长。所以它要**耐拉伸**：主干贯穿整幅、
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


# ---------------------------------------------------------------- 电球

def orb(size=128) -> Image.Image:
    rng = np.random.default_rng(SEED)
    c = size / 2.0
    r = radial(size, size, c, c)
    core_r = size * 0.21

    body = np.clip(1.0 - r / core_r, 0.0, 1.0) ** 0.6           # 实心核
    halo = np.exp(-((r - core_r) / (size * 0.115)) ** 2)         # 外圈辉光
    halo[r < core_r] = 1.0

    # 「破损」：一道贯穿核心的裂缝（挖掉光），外加一圈碎裂的缺口
    crack = polyline_mask(size, size, jagged(rng, c - core_r * 1.15, c - core_r * 0.75,
                                             c + core_r * 1.15, c + core_r * 0.62, 5, core_r * 0.30), 2.6)
    chip = polyline_mask(size, size, jagged(rng, c + core_r * 0.30, c - core_r * 1.05,
                                            c + core_r * 1.02, c - core_r * 0.10, 3, core_r * 0.22), 2.0)
    broken = np.clip(crack + chip, 0.0, 1.0)
    body = np.clip(body - broken * 0.85, 0.0, 1.0)

    # 环绕电弧：三道从核心边缘窜出去的锯齿
    arcs = np.zeros((size, size))
    for k in range(3):
        a0 = rng.uniform(0, 2 * math.pi)
        a1 = a0 + rng.uniform(1.1, 2.2) * (1 if k % 2 else -1)
        r0, r1 = core_r * 0.92, size * 0.44
        arcs = np.maximum(arcs, polyline_mask(
            size, size,
            jagged(rng, c + r0 * math.cos(a0), c + r0 * math.sin(a0),
                   c + r1 * math.cos(a1), c + r1 * math.sin(a1), 6, size * 0.055),
            1.5))
    arcs = np.clip(arcs + glow(arcs, 2.2) * 0.8, 0.0, 1.0)
    arcs[r > size * 0.47] = 0.0                                  # 别顶到贴图边

    inten = np.clip(body + halo * 0.55 + arcs * 0.95, 0.0, 1.4)
    hot = np.clip((inten - 0.55) / 0.45, 0.0, 1.0)                # 越亮越白
    rgb = np.stack([0.16 + 0.84 * hot,
                    0.62 + 0.38 * hot,
                    np.full_like(hot, 1.0)], axis=2)
    return to_image(rgb, np.clip(inten, 0.0, 1.0))


# ---------------------------------------------------------------- 闪电弹

def bolt(w=256, h=64) -> Image.Image:
    rng = np.random.default_rng(SEED + 1)
    spine = jagged(rng, 0.0, h / 2, float(w), h / 2, 11, h * 0.22)   # 主干贯穿整幅（要耐横向拉伸）
    core = polyline_mask(h, w, spine, 1.8)
    branches = np.zeros((h, w))
    for i in (2, 5, 8):                                          # 三条小分叉
        bx, by = spine[i]
        branches = np.maximum(branches, polyline_mask(
            h, w, jagged(rng, bx, by, bx + rng.uniform(14, 30), by + rng.uniform(-18, 18), 3, 5.0), 1.2))
    line = np.clip(core + branches * 0.65, 0.0, 1.0)
    inten = np.clip(line + glow(line, 2.0) * 1.1 + glow(line, 7.0) * 0.8, 0.0, 1.5)

    x = np.mgrid[0:h, 0:w][1].astype(np.float64)
    inten *= np.clip(x / 12.0, 0.0, 1.0)                          # 只在左端（电球那头）收一点

    hot = np.clip((inten - 0.5) / 0.5, 0.0, 1.0)
    rgb = np.stack([0.30 + 0.70 * hot,
                    0.72 + 0.28 * hot,
                    np.full_like(hot, 1.0)], axis=2)
    return to_image(rgb, np.clip(inten, 0.0, 1.0))


# ---------------------------------------------------------------- 卡图画面

def card_face(w=512, h=640) -> Image.Image:
    rng = np.random.default_rng(SEED + 2)
    cx, cy = w / 2.0, h * 0.46
    r = radial(h, w, cx, cy)
    core_r = w * 0.20

    bg = np.clip(0.16 - r / (w * 2.6), 0.02, 0.16)                # 中间略亮的深底
    ring = np.exp(-((r - w * 0.34) / (w * 0.012)) ** 2) * 0.45     # 一圈约束环
    for k in range(6):                                            # 环上的缺口
        a = 2 * math.pi * k / 6 + 0.3
        ring[radial(h, w, cx + w * 0.34 * math.cos(a), cy + w * 0.34 * math.sin(a)) < w * 0.035] = 0.0

    body = np.clip(1.0 - r / core_r, 0.0, 1.0) ** 0.55
    halo = np.exp(-((r - core_r) / (w * 0.10)) ** 2)
    halo[r < core_r] = 1.0

    crack = polyline_mask(h, w, jagged(rng, cx - core_r * 1.2, cy - core_r * 0.8,
                                       cx + core_r * 1.2, cy + core_r * 0.7, 6, core_r * 0.28), 7.0)
    chip = polyline_mask(h, w, jagged(rng, cx + core_r * 0.25, cy - core_r * 1.1,
                                      cx + core_r * 1.05, cy - core_r * 0.05, 4, core_r * 0.20), 5.0)
    body = np.clip(body - np.clip(crack + chip, 0, 1) * 0.9, 0.0, 1.0)

    arcs = np.zeros((h, w))
    for k in range(5):
        a0 = 2 * math.pi * k / 5 + rng.uniform(-0.4, 0.4)
        a1 = a0 + rng.uniform(0.5, 1.4) * (1 if k % 2 else -1)
        arcs = np.maximum(arcs, polyline_mask(
            h, w,
            jagged(rng, cx + core_r * 0.95 * math.cos(a0), cy + core_r * 0.95 * math.sin(a0),
                   cx + w * 0.345 * math.cos(a1), cy + w * 0.345 * math.sin(a1), 7, w * 0.030),
            3.0))
    arcs = np.clip(arcs + glow(arcs, 4.0) * 0.9, 0.0, 1.0)

    light = np.clip(body * 1.15 + halo * 0.55 + arcs * 0.9 + ring, 0.0, 1.5)
    hot = np.clip((light - 0.5) / 0.5, 0.0, 1.0)
    rgb = np.stack([bg * 0.5 + light * (0.14 + 0.86 * hot),
                    bg * 0.8 + light * (0.60 + 0.40 * hot),
                    bg * 1.6 + light * 1.0], axis=2)
    return to_image(np.clip(rgb, 0.0, 1.0), np.ones((h, w)))


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
