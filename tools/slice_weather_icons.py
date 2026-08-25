#!/usr/bin/env python3
"""Slice tools/assets/weather_sheet2.png into transparent icons.

The sheet is a 6x4 grid of neon weather glyphs over a heavily blurred haze,
with a sleep moon floating in the top band. Every weather glyph is a thin
bright stroke - the clouds and crescents are hollow outlines, not filled
shapes - so the haze is removed with a morphological top-hat: open the image
with a window wider than the stroke to estimate the background, then keep
whatever stands above it. The same runs on blue-ness and yellow-ness channels
so the neon drops, bolts, snowflakes and sun cores survive even where the haze
itself is blue.

The sleep moon is blue-on-blue with almost no luminance contrast, so it gets a
plain blue-channel threshold instead.
"""
from PIL import Image, ImageFilter
import numpy as np
from collections import deque
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent
SHEET = ROOT / "assets/weather_sheet2.png"
RES = ROOT.parent / "watchface/src/main/res/drawable-nodpi"

CELL_W, CELL_H = 256, 203
GRID_TOP = 210
PAD = 30          # crop beyond the cell so glyphs are never clipped
OUT_SIZE = 96

BLUE = np.array([59, 130, 246], dtype=np.float32)
YELLOW = np.array([250, 204, 21], dtype=np.float32)

# (row, col) -> (output drawable, solid)
# `solid` widens the top-hat window for glyphs painted as filled shapes rather
# than outlines - their flat interiors are invisible to the narrow window.
MAPPING = {
    (0, 0): ("wx_clear.png", False),        # sun
    (0, 1): ("wx_partly.png", False),       # sun behind cloud
    (0, 3): ("wx_cloudy.png", False),       # plain cloud
    (1, 1): ("wx_rain.png", False),         # cloud + two drops
    (1, 5): ("wx_snow.png", False),         # cloud + snowflakes
    (2, 3): ("wx_thunder.png", False),      # cloud + bolt + drops
    (3, 4): ("wx_night.png", False),        # crescent + sparkles
    (3, 3): ("wx_night_cloud.png", True),   # crescent + filled cloud
}

SLEEP_BOX = (640, 0, 896, 210)
SLEEP_BLUE_MIN = 251


def opening(chan, passes=4, size=9):
    """Morphological opening: wipes bright structures thinner than the window."""
    img = Image.fromarray(np.clip(chan, 0, 255).astype(np.uint8), "L")
    for _ in range(passes):
        img = img.filter(ImageFilter.MinFilter(size))
    for _ in range(passes):
        img = img.filter(ImageFilter.MaxFilter(size))
    return np.asarray(img, dtype=np.float32)


def closing(chan, passes=4, size=9):
    """Morphological closing: wipes dark structures thinner than the window."""
    img = Image.fromarray(np.clip(chan, 0, 255).astype(np.uint8), "L")
    for _ in range(passes):
        img = img.filter(ImageFilter.MaxFilter(size))
    for _ in range(passes):
        img = img.filter(ImageFilter.MinFilter(size))
    return np.asarray(img, dtype=np.float32)


def tophat(chan):
    """How far a pixel stands above the local background."""
    return np.clip(chan - opening(chan), 0, 255)


def bottomhat(chan):
    """How far a pixel sits below the local background."""
    return np.clip(closing(chan) - chan, 0, 255)


def soft(x, lo, hi):
    return np.clip((x - lo) / float(hi - lo), 0.0, 1.0)


def alpha_map(cell, solid=False):
    """Glyph pixels are near-pure white, neon blue or yellow AND locally stand
    out from the haze. Either test alone fails: the haze reaches white in the
    bright cells, and it goes deep blue in the dark ones."""
    a = np.asarray(cell.convert("RGB"), dtype=np.float32)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    hi, lo = a.max(axis=2), a.min(axis=2)
    lum = r * 0.3 + g * 0.6 + b * 0.1

    stands_out = tophat(lum) > 10
    if solid:
        stands_out |= np.clip(lum - opening(lum, passes=12), 0, 255) > 14
    white = (lo >= 225) & (hi - lo <= 28) & stands_out
    # neon blue: red dives to near zero while blue pins at ~250
    blue = (r <= 45) & (b >= 235) & (bottomhat(r) > 8)
    yellow = (r >= 225) & (g >= 185) & (b <= 130)

    mask = Image.fromarray(((white | blue | yellow) * 255).astype(np.uint8), "L")
    mask = mask.filter(ImageFilter.MedianFilter(5))   # smooth ragged stroke edges
    return np.asarray(mask, dtype=np.float32) / 255.0


def keep_central(alpha, inner, min_frac=0.0012, thresh=0.5):
    """Keep blobs big enough and centred in `inner`; drops crumbs and neighbours."""
    mask = alpha > thresh
    h, w = mask.shape
    x0, y0, x1, y1 = inner
    seen = np.zeros((h, w), dtype=bool)
    keep = np.zeros((h, w), dtype=bool)
    limit = max(40, int(h * w * min_frac))
    for sy in range(h):
        for sx in range(w):
            if not mask[sy, sx] or seen[sy, sx]:
                continue
            comp, dq = [], deque([(sy, sx)])
            seen[sy, sx] = True
            while dq:
                y, x = dq.popleft()
                comp.append((y, x))
                for ny in (y - 1, y, y + 1):
                    for nx in (x - 1, x, x + 1):
                        if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = True
                            dq.append((ny, nx))
            if len(comp) < limit:
                continue
            cy = sum(p[0] for p in comp) / len(comp)
            cx = sum(p[1] for p in comp) / len(comp)
            if x0 <= cx <= x1 and y0 <= cy <= y1:
                for y, x in comp:
                    keep[y, x] = True
    return keep.astype(np.float32)


def recolor(cell):
    """Flatten the washed-out glyph colours back to white / neon blue / yellow."""
    a = np.asarray(cell.convert("RGB"), dtype=np.float32)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    bluish = (b - (r + g) * 0.5) > 45
    yellowish = ((r + g) * 0.5 - b) > 45

    out = np.full_like(a, 255.0)
    out[bluish] = BLUE
    out[yellowish] = YELLOW
    return out.astype(np.uint8)


def to_rgba(cell, alpha):
    img = Image.fromarray((np.clip(alpha, 0, 1) * 255).astype(np.uint8), "L")
    img = img.filter(ImageFilter.GaussianBlur(0.6))
    return Image.fromarray(np.dstack([recolor(cell), np.asarray(img)]), "RGBA")


def extract_weather(cell, solid=False):
    inner = (PAD, PAD, cell.width - PAD, cell.height - PAD)
    return to_rgba(cell, keep_central(alpha_map(cell, solid), inner))


def extract_sleep(cell):
    b = np.asarray(cell.convert("RGB"), dtype=np.int16)[:, :, 2]
    alpha = soft(b.astype(np.float32), SLEEP_BLUE_MIN - 3, SLEEP_BLUE_MIN)
    inner = (20, 20, cell.width - 20, cell.height - 20)
    alpha = keep_central(alpha, inner, min_frac=0.004)
    rgb = np.zeros(b.shape + (3,), dtype=np.uint8)
    rgb[:, :] = BLUE.astype(np.uint8)
    img = Image.fromarray((np.clip(alpha, 0, 1) * 255).astype(np.uint8), "L")
    img = img.filter(ImageFilter.GaussianBlur(0.6))
    return Image.fromarray(np.dstack([rgb, np.asarray(img)]), "RGBA")


def tight_square(img, pad_ratio=0.05):
    img = img.crop(img.getbbox())
    side = max(img.size) + 2 * int(max(img.size) * pad_ratio)
    sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    sq.paste(img, ((side - img.width) // 2, (side - img.height) // 2), img)
    return sq.resize((OUT_SIZE, OUT_SIZE), Image.LANCZOS)


def main():
    sheet = Image.open(SHEET)
    for (row, col), (name, solid) in MAPPING.items():
        box = (col * CELL_W - PAD, GRID_TOP + row * CELL_H - PAD,
               (col + 1) * CELL_W + PAD, GRID_TOP + (row + 1) * CELL_H + PAD)
        tight_square(extract_weather(sheet.crop(box), solid)).save(RES / name)
        print("wrote", RES / name)

    tight_square(extract_sleep(sheet.crop(SLEEP_BOX))).save(RES / "ic_sleep.png")
    print("wrote", RES / "ic_sleep.png")


if __name__ == "__main__":
    main()
