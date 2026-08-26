#!/usr/bin/env python3
"""Slice tools/assets/weather_sheet3.png into the watch face weather icons.

The sheet is a 6x4 grid of neon weather glyphs already cut out on transparency,
so there is no background to strip - just crop each cell, drop the stray specks
the cut-out left behind, and square everything up to a common size.
"""
from PIL import Image, ImageFilter
import numpy as np
from collections import deque
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent
SHEET = ROOT / "assets/weather_sheet3.png"
RES = ROOT.parent / "watchface/src/main/res/drawable-nodpi"

COLS, ROWS = 6, 4
OUT_SIZE = 96
ALPHA_FLOOR = 40      # below this a pixel is treated as background
MIN_BLOB = 150       # px; anything smaller is cut-out noise

# (row, col) -> output drawable
MAPPING = {
    (0, 0): "wx_clear.png",        # sun
    (0, 1): "wx_partly.png",       # sun behind cloud
    (0, 3): "wx_cloudy.png",       # plain cloud
    (1, 1): "wx_rain.png",         # cloud + two drops
    (1, 5): "wx_snow.png",         # cloud + snowflakes
    (2, 2): "wx_thunder.png",      # cloud + bolt + drop
    (3, 3): "wx_night.png",        # crescent + sparkles
    (3, 5): "wx_night_cloud.png",  # crescent + cloud
}


def cell_box(row, col, w, h):
    cw, ch = w / COLS, h / ROWS
    return (int(col * cw), int(row * ch), int((col + 1) * cw), int((row + 1) * ch))


def drop_specks(alpha):
    """Keep only blobs of a sensible size; the cut-out leaves pepper noise."""
    solid = alpha >= ALPHA_FLOOR
    h, w = solid.shape
    seen = np.zeros((h, w), dtype=bool)
    keep = np.zeros((h, w), dtype=bool)
    for sy in range(h):
        for sx in range(w):
            if not solid[sy, sx] or seen[sy, sx]:
                continue
            comp, dq = [], deque([(sy, sx)])
            seen[sy, sx] = True
            while dq:
                y, x = dq.popleft()
                comp.append((y, x))
                for ny in (y - 1, y, y + 1):
                    for nx in (x - 1, x, x + 1):
                        if 0 <= ny < h and 0 <= nx < w and solid[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = True
                            dq.append((ny, nx))
            if len(comp) >= MIN_BLOB:
                for y, x in comp:
                    keep[y, x] = True
    # let the surviving blobs keep their soft anti-aliased rim
    grown = np.asarray(
        Image.fromarray((keep * 255).astype(np.uint8), "L").filter(ImageFilter.MaxFilter(5)),
        dtype=np.float32) / 255.0
    return (alpha * grown).astype(np.uint8)


def clean(cell):
    a = np.asarray(cell.convert("RGBA")).copy()
    a[:, :, 3] = drop_specks(a[:, :, 3])
    return Image.fromarray(a, "RGBA")


def tight_square(img, pad_ratio=0.05):
    img = img.crop(img.getbbox())
    side = max(img.size) + 2 * int(max(img.size) * pad_ratio)
    sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    sq.paste(img, ((side - img.width) // 2, (side - img.height) // 2), img)
    return sq.resize((OUT_SIZE, OUT_SIZE), Image.LANCZOS)


def main():
    sheet = Image.open(SHEET).convert("RGBA")
    w, h = sheet.size
    for (row, col), name in MAPPING.items():
        icon = tight_square(clean(sheet.crop(cell_box(row, col, w, h))))
        icon.save(RES / name)
        print("wrote", RES / name)


if __name__ == "__main__":
    main()
