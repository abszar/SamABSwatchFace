#!/usr/bin/env python3
"""Generate static drawables for the SamAB watch face."""
from PIL import Image, ImageDraw, ImageChops
import math
import pathlib

RES = pathlib.Path(__file__).resolve().parent.parent / "watchface/src/main/res/drawable-nodpi"
S = 4  # supersampling factor

BLUE = (59, 130, 246, 255)
WHITE = (255, 255, 255, 255)
GREEN = (34, 197, 94, 255)
PURPLE = (124, 92, 255, 255)
YELLOW = (250, 204, 21, 255)


def canvas(w=64, h=64):
    return Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))


def save(img, name, w=64, h=64):
    img.resize((w, h), Image.LANCZOS).save(RES / name)
    print("wrote", RES / name)


def sun(d, cx, cy, r, color, rays=8, ray_len=7, ray_gap=4):
    d.ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S],
              outline=color, width=3 * S)
    for i in range(rays):
        a = math.radians(i * 360 / rays)
        r1, r2 = r + ray_gap, r + ray_gap + ray_len
        d.line([(cx + r1 * math.cos(a)) * S, (cy + r1 * math.sin(a)) * S,
                (cx + r2 * math.cos(a)) * S, (cy + r2 * math.sin(a)) * S],
               fill=color, width=3 * S)


def cloud(d, cx, cy, scale, color):
    """Filled cloud centered-ish at cx,cy; scale 1.0 spans ~40px wide."""
    def e(x, y, r):
        d.ellipse([(cx + (x - r) * scale) * S, (cy + (y - r) * scale) * S,
                   (cx + (x + r) * scale) * S, (cy + (y + r) * scale) * S], fill=color)
    e(-12, 4, 8)
    e(0, -2, 11)
    e(12, 5, 7)
    d.rounded_rectangle([(cx - 18 * scale) * S, (cy + 2 * scale) * S,
                         (cx + 18 * scale) * S, (cy + 12 * scale) * S],
                        radius=int(5 * scale * S), fill=color)


def crescent(cx, cy, r, color, w=64, h=64):
    """Return an RGBA layer with a moon crescent."""
    base = canvas(w, h)
    d = ImageDraw.Draw(base)
    d.ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S], fill=color)
    mask = Image.new("L", base.size, 0)
    dm = ImageDraw.Draw(mask)
    off = r * 0.62
    dm.ellipse([(cx - r + off) * S, (cy - r - off * 0.7) * S,
                (cx + r + off) * S, (cy + r - off * 0.7) * S], fill=255)
    base.putalpha(ImageChops.subtract(base.getchannel("A"), mask))
    return base


def star(d, cx, cy, r, color):
    d.line([(cx - r) * S, cy * S, (cx + r) * S, cy * S], fill=color, width=2 * S)
    d.line([cx * S, (cy - r) * S, cx * S, (cy + r) * S], fill=color, width=2 * S)


def gen_bg():
    img = canvas(450, 450)
    d = ImageDraw.Draw(img)
    c = 225 * S
    for i in range(60):
        a = math.radians(i * 6 - 90)
        major = (i % 5 == 0)
        r1 = (225 - (14 if major else 8)) * S
        r2 = 223 * S
        col = (255, 255, 255, 230 if major else 100)
        d.line([c + r1 * math.cos(a), c + r1 * math.sin(a),
                c + r2 * math.cos(a), c + r2 * math.sin(a)],
               fill=col, width=(3 if major else 2) * S)
    d.line([60 * S, 366 * S, 390 * S, 366 * S], fill=(255, 255, 255, 50), width=1 * S)
    SEP = (255, 255, 255, 50)
    d.line([225 * S, 30 * S, 225 * S, 78 * S], fill=(255, 255, 255, 90), width=1 * S)  # weather | sleep
    d.line([45 * S, 285 * S, 405 * S, 285 * S], fill=SEP, width=1 * S)     # under day strip
    for x in (93, 159, 225, 291, 357):                                     # forecast columns
        d.line([x * S, 300 * S, x * S, 350 * S], fill=SEP, width=1 * S)
    for x in (193, 257):                                                   # bottom row
        d.line([x * S, 380 * S, x * S, 428 * S], fill=SEP, width=1 * S)
    save(img, "bg.png", 450, 450)


def gen_tri_down():
    img = canvas(16, 8)
    d = ImageDraw.Draw(img)
    d.polygon([(1 * S, 1 * S), (15 * S, 1 * S), (8 * S, 7 * S)], fill=BLUE)
    save(img, "tri_down.png", 16, 8)


def gen_wx_clear():
    img = canvas()
    sun(ImageDraw.Draw(img), 32, 32, 11, BLUE)
    save(img, "wx_clear.png")


def gen_wx_partly():
    img = canvas()
    d = ImageDraw.Draw(img)
    sun(d, 42, 22, 8, BLUE, rays=8, ray_len=5, ray_gap=3)
    cloud(d, 28, 38, 0.9, WHITE)
    save(img, "wx_partly.png")


def gen_wx_cloudy():
    img = canvas()
    cloud(ImageDraw.Draw(img), 32, 32, 1.0, WHITE)
    save(img, "wx_cloudy.png")


def gen_wx_rain():
    img = canvas()
    d = ImageDraw.Draw(img)
    cloud(d, 32, 26, 0.9, WHITE)
    for x in (22, 32, 42):
        d.line([x * S, 44 * S, (x - 4) * S, 56 * S], fill=BLUE, width=3 * S)
    save(img, "wx_rain.png")


def gen_wx_snow():
    img = canvas()
    d = ImageDraw.Draw(img)
    cloud(d, 32, 26, 0.9, WHITE)
    for x in (22, 32, 42):
        d.ellipse([(x - 2) * S, 48 * S, (x + 2) * S, 52 * S], fill=WHITE)
    save(img, "wx_snow.png")


def gen_wx_thunder():
    img = canvas()
    d = ImageDraw.Draw(img)
    cloud(d, 32, 24, 0.9, WHITE)
    bolt = [(34, 38), (26, 50), (32, 50), (28, 60), (40, 46), (33, 46), (38, 38)]
    d.polygon([(x * S, y * S) for x, y in bolt], fill=YELLOW)
    save(img, "wx_thunder.png")


def gen_wx_night():
    img = crescent(30, 34, 14, WHITE)
    d = ImageDraw.Draw(img)
    star(d, 48, 18, 4, WHITE)
    star(d, 52, 34, 3, WHITE)
    save(img, "wx_night.png")


def gen_wx_night_cloud():
    img = crescent(26, 26, 12, WHITE)
    d = ImageDraw.Draw(img)
    cloud(d, 38, 44, 0.7, WHITE)
    star(d, 52, 20, 3, WHITE)
    save(img, "wx_night_cloud.png")


def gen_ic_link():
    img = canvas()
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([8 * S, 24 * S, 34 * S, 40 * S], radius=8 * S,
                        outline=BLUE, width=4 * S)
    d.rounded_rectangle([30 * S, 24 * S, 56 * S, 40 * S], radius=8 * S,
                        outline=BLUE, width=4 * S)
    d.line([26 * S, 32 * S, 38 * S, 32 * S], fill=BLUE, width=4 * S)
    save(img, "ic_link.png")


def gen_ic_shoe():
    img = canvas()
    d = ImageDraw.Draw(img)
    body = [(10, 40), (18, 24), (26, 24), (34, 34), (54, 40), (54, 46), (10, 46)]
    d.polygon([(x * S, y * S) for x, y in body], fill=GREEN)
    d.line([28 * S, 30 * S, 34 * S, 26 * S], fill=(0, 0, 0, 255), width=2 * S)
    save(img, "ic_shoe.png")


def gen_ic_watch():
    img = canvas()
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([22 * S, 6 * S, 42 * S, 16 * S], radius=3 * S, fill=WHITE)
    d.rounded_rectangle([22 * S, 48 * S, 42 * S, 58 * S], radius=3 * S, fill=WHITE)
    d.rounded_rectangle([18 * S, 16 * S, 46 * S, 48 * S], radius=8 * S,
                        outline=WHITE, width=4 * S)
    save(img, "ic_watch.png")


def gen_ic_phone():
    img = canvas()
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([20 * S, 6 * S, 44 * S, 58 * S], radius=6 * S,
                        outline=WHITE, width=4 * S)
    d.ellipse([30 * S, 48 * S, 34 * S, 52 * S], fill=WHITE)
    save(img, "ic_phone.png")


def gen_ic_sleep():
    img = crescent(28, 36, 14, PURPLE)
    d = ImageDraw.Draw(img)
    for cx, cy, r in ((46, 16, 5), (54, 28, 3)):
        d.line([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy - r) * S], fill=BLUE, width=2 * S)
        d.line([(cx + r) * S, (cy - r) * S, (cx - r) * S, (cy + r) * S], fill=BLUE, width=2 * S)
        d.line([(cx - r) * S, (cy + r) * S, (cx + r) * S, (cy + r) * S], fill=BLUE, width=2 * S)
    save(img, "ic_sleep.png")


def main():
    RES.mkdir(parents=True, exist_ok=True)
    gen_bg()
    gen_tri_down()
    gen_wx_clear()
    gen_wx_partly()
    gen_wx_cloudy()
    gen_wx_rain()
    gen_wx_snow()
    gen_wx_thunder()
    gen_wx_night()
    gen_wx_night_cloud()
    gen_ic_link()
    gen_ic_shoe()
    gen_ic_watch()
    gen_ic_phone()
    gen_ic_sleep()


if __name__ == "__main__":
    main()
