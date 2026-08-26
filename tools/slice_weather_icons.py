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
PAD_RATIO = 0.05     # breathing room around a glyph, as a fraction of its size
BLUE = (59, 130, 246)

# (row, col) -> output drawable, plus per-icon overrides:
#   pad   - shrink the margin so a wide glyph fills more of the square
#   blue  - repaint the sheet's yellow sun in the face's accent blue
MAPPING = {
    (0, 0): ("wx_clear.png", {}),                        # sun
    (0, 2): ("wx_partly.png", {"pad": 0.0, "blue": True}),  # big cloud + sun
    (0, 3): ("wx_cloudy.png", {}),                       # plain cloud
    (0, 5): ("wx_fog.png", {}),                          # cloud + fog bars
    (1, 0): ("wx_light_rain.png", {}),                   # cloud + one drop
    (1, 1): ("wx_rain.png", {}),                         # cloud + two drops
    (1, 2): ("wx_heavy_rain.png", {}),                   # cloud + three drops
    (1, 3): ("wx_sleet.png", {}),                        # cloud + drop + flake
    (1, 4): ("wx_snow.png", {}),                         # cloud + two flakes
    (1, 5): ("wx_heavy_snow.png", {}),                   # cloud + three flakes
    (2, 0): ("wx_light_snow.png", {}),                   # cloud + snow specks
    (2, 2): ("wx_thunder.png", {}),                      # cloud + bolt + drop
    (2, 5): ("wx_windy.png", {}),                        # wind swirls
    (3, 3): ("wx_night.png", {}),                        # crescent + sparkles
    (3, 5): ("wx_night_cloud.png", {}),                  # crescent + cloud
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


def bluify(cell):
    """Repaint the sheet's yellow sun in the accent blue, edge pixels included."""
    a = np.asarray(cell.convert("RGBA")).copy()
    r, g, b = a[:, :, 0].astype(int), a[:, :, 1].astype(int), a[:, :, 2].astype(int)
    yellow = (r - b > 60) & (g - b > 30)
    for c, v in enumerate(BLUE):
        a[:, :, c] = np.where(yellow, v, a[:, :, c])
    return Image.fromarray(a, "RGBA")


def tight_square(img, pad_ratio=PAD_RATIO):
    img = img.crop(img.getbbox())
    side = max(img.size) + 2 * int(max(img.size) * pad_ratio)
    sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    sq.paste(img, ((side - img.width) // 2, (side - img.height) // 2), img)
    return sq.resize((OUT_SIZE, OUT_SIZE), Image.LANCZOS)


def main():
    sheet = Image.open(SHEET).convert("RGBA")
    w, h = sheet.size
    for (row, col), (name, opts) in MAPPING.items():
        cell = clean(sheet.crop(cell_box(row, col, w, h)))
        if opts.get("blue"):
            cell = bluify(cell)
        icon = tight_square(cell, opts.get("pad", PAD_RATIO))
        icon.save(RES / name)
        print("wrote", RES / name)


if __name__ == "__main__":
    main()
