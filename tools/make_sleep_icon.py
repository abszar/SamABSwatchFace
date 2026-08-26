#!/usr/bin/env python3
"""Square up tools/assets/sleep_icon.png into the sleep complication drawable.

The artwork arrives already cut out on transparency and wider than it is tall,
so it just needs trimming to its ink and centring on a square canvas - the
complication draws it into a 40x40 box.
"""
import pathlib

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent
SRC = ROOT / "assets/sleep_icon.png"
OUT = ROOT.parent / "watchface/src/main/res/drawable-nodpi/ic_sleep.png"

OUT_SIZE = 96
PAD_RATIO = 0.04
ALPHA_FLOOR = 12          # clear the near-invisible fringe the cut-out leaves


def main():
    img = Image.open(SRC).convert("RGBA")
    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = px[x, y]
            if a < ALPHA_FLOOR:
                px[x, y] = (0, 0, 0, 0)

    img = img.crop(img.getbbox())
    side = max(img.size)
    side += 2 * int(side * PAD_RATIO)
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.paste(img, ((side - img.width) // 2, (side - img.height) // 2), img)
    square.resize((OUT_SIZE, OUT_SIZE), Image.LANCZOS).save(OUT)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
