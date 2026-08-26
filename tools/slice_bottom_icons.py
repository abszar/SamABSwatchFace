#!/usr/bin/env python3
"""Slice tools/assets/bottom_icons.png into the watch, phone and shoe drawables.

The three glyphs sit side by side on transparency. They are drawn for a dark
background - the black areas are meant to read as the background showing
through - so the only work is cutting them apart and squaring them up.
"""
import pathlib
from collections import deque

import numpy as np
from PIL import Image, ImageFilter

ROOT = pathlib.Path(__file__).resolve().parent
SHEET = ROOT / "assets/bottom_icons.png"
RES = ROOT.parent / "watchface/src/main/res/drawable-nodpi"

OUT_SIZE = 96
PAD_RATIO = 0.04
ALPHA_FLOOR = 40
COL_GAP = 30
NAMES = ["ic_watch.png", "ic_phone.png", "ic_shoe.png"]


def column_groups(mask):
    on = mask.any(axis=0)
    runs, start, last = [], None, None
    for i, v in enumerate(on):
        if v:
            if start is None:
                start = i
            last = i
        elif start is not None and i - last > COL_GAP:
            runs.append((start, last))
            start = None
    if start is not None:
        runs.append((start, last))
    return runs


def tight_square(img):
    img = img.crop(img.getbbox())
    side = max(img.size)
    side += 2 * int(side * PAD_RATIO)
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.paste(img, ((side - img.width) // 2, (side - img.height) // 2), img)
    return square.resize((OUT_SIZE, OUT_SIZE), Image.LANCZOS)


def main():
    sheet = Image.open(SHEET).convert("RGBA")
    mask = np.asarray(sheet)[:, :, 3] > ALPHA_FLOOR
    groups = column_groups(mask)
    assert len(groups) == len(NAMES), "expected %d glyphs, found %d" % (len(NAMES), len(groups))

    for (x0, x1), name in zip(groups, NAMES):
        cell = sheet.crop((x0, 0, x1 + 1, sheet.height))
        tight_square(cell).save(RES / name)
        print("wrote", RES / name)


if __name__ == "__main__":
    main()
