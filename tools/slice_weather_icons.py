#!/usr/bin/env python3
"""Slice tools/assets/weather_sheet.png (5x4 grid) into transparent wx_* icons.

Each icon sits on a mottled dark photo background but is ringed by a bright
glow. A BFS flood fill from the cell borders travels only through
darker-than-glow pixels, so it eats the background and stops at the glow,
leaving the icon (including its black outlines) untouched.
"""
from PIL import Image
import numpy as np
from collections import deque
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent
SHEET = ROOT / "assets/weather_sheet.png"
RES = ROOT.parent / "watchface/src/main/res/drawable-nodpi"

COLS, ROWS = 5, 4
OUT_SIZE = 96
LUMA_BG_MAX = 165  # flood fill may pass through pixels darker than this

# cell index (row-major) -> output drawable name
MAPPING = {
    0: "wx_clear.png",         # sun
    1: "wx_partly.png",        # sun behind white cloud
    4: "wx_cloudy.png",        # gray cloud
    6: "wx_rain.png",          # gray cloud, rain drops
    7: "wx_thunder.png",       # cloud with lightning
    9: "wx_snow.png",          # cloud with snowflakes
    10: "wx_night.png",        # moon and stars
    11: "wx_night_cloud.png",  # moon with cloud
}


def cut_cell(img, idx):
    w, h = img.size
    cw, ch = w // COLS, h // ROWS
    r, c = divmod(idx, COLS)
    return img.crop((c * cw, r * ch, (c + 1) * cw, (r + 1) * ch))


def remove_bg(cell):
    rgb = np.asarray(cell.convert("RGB"), dtype=np.int16)
    h, w, _ = rgb.shape
    luma = (rgb[:, :, 0] * 3 + rgb[:, :, 1] * 6 + rgb[:, :, 2]) // 10
    sat = rgb.max(axis=2) - rgb.min(axis=2)
    passable = (luma < LUMA_BG_MAX) & (sat < 70)
    bg = np.zeros((h, w), dtype=bool)
    dq = deque()
    for x in range(w):
        for y in (0, h - 1):
            if passable[y, x] and not bg[y, x]:
                bg[y, x] = True
                dq.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if passable[y, x] and not bg[y, x]:
                bg[y, x] = True
                dq.append((y, x))
    while dq:
        y, x = dq.popleft()
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < h and 0 <= nx < w and passable[ny, nx] and not bg[ny, nx]:
                bg[ny, nx] = True
                dq.append((ny, nx))
    out = np.dstack([np.asarray(cell.convert("RGB"), dtype=np.uint8),
                     np.where(bg, 0, 255).astype(np.uint8)])
    return Image.fromarray(out, "RGBA")


def tight_square(img, pad_ratio=0.04):
    bbox = img.getbbox()
    img = img.crop(bbox)
    side = max(img.size)
    pad = int(side * pad_ratio)
    side += 2 * pad
    sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    sq.paste(img, ((side - img.width) // 2, (side - img.height) // 2), img)
    return sq.resize((OUT_SIZE, OUT_SIZE), Image.LANCZOS)


def main():
    sheet = Image.open(SHEET)
    for idx, name in MAPPING.items():
        icon = tight_square(remove_bg(cut_cell(sheet, idx)))
        icon.save(RES / name)
        print("wrote", RES / name)


if __name__ == "__main__":
    main()
