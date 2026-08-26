#!/usr/bin/env python3
"""Build res/font/clockdigits.ttf from tools/assets/clock_digits.png.

The sheet holds 0-4 on one row and 5-9 on the next. Each digit is traced to
outlines with potrace, normalised to a common height and baseline, and given a
uniform (tabular) advance so the clock never shifts as the time changes.

A real font is the cheap way to do this on a watch: the system text engine
caches rendered glyphs, so a ten-glyph face costs no more per frame than the
built-in one, and the file is a few KB rather than a pile of PNGs.
"""
import pathlib

import numpy as np
import potrace
from PIL import Image
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.ttGlyphPen import TTGlyphPen

ROOT = pathlib.Path(__file__).resolve().parent
SHEET = ROOT / "assets/clock_digits.png"
OUT = ROOT.parent / "watchface/src/main/res/font/clockdigits.ttf"

UPM = 1000
DIGIT_HEIGHT = 700        # baseline to top of a digit, in font units
SIDE_BEARING = 20         # padding either side of the widest digit
INK_MAX_LUMA = 128        # the sheet is dark ink on a light checkerboard
ROW_GAP = 20              # min blank rows separating the two digit rows
MIN_ROW_FRACTION = 0.2    # a digit row is tall; the stray colon sample is not
COL_GAP = 8               # min blank cols separating digits
CURVE_ERROR = 1.0         # cubic -> quadratic tolerance, font units

FAMILY = "clockdigits"
STYLE = "Regular"


def runs(flags, gap):
    """Index ranges of True, merging breaks shorter than `gap`."""
    out, start, last = [], None, None
    for i, on in enumerate(flags):
        if on:
            if start is None:
                start = i
            last = i
        elif start is not None and i - last > gap:
            out.append((start, last))
            start = None
    if start is not None:
        out.append((start, last))
    return out


def find_digits(ink):
    """Return the ten digit bitmaps in 0-9 order, top row first."""
    bands = runs(ink.any(axis=1), ROW_GAP)
    # drops the loose colon sample sitting under the digits
    bands = [b for b in bands if b[1] - b[0] > ink.shape[0] * MIN_ROW_FRACTION]
    assert len(bands) == 2, "expected two digit rows, got %d" % len(bands)

    cells = []
    for y0, y1 in bands:
        band = ink[y0:y1 + 1]
        cols = runs(band.any(axis=0), COL_GAP)
        assert len(cols) == 5, "expected 5 digits per row, got %d" % len(cols)
        for x0, x1 in cols:
            sub = band[:, x0:x1 + 1]
            rows = np.where(sub.any(axis=1))[0]
            cells.append(sub[rows.min():rows.max() + 1])
    return cells


def trace(bitmap):
    """Trace a bool bitmap into contours of (points, is_hole) in y-up units."""
    # potrace inverts a bool bitmap internally, so hand it the inverse of the ink
    path = potrace.Bitmap(~bitmap).trace()
    h = bitmap.shape[0]
    contours = []
    for curve in path:
        pts = []

        def pt(p):
            # potrace works in image space (y down); flip to font space (y up)
            return (float(p.x), float(h - p.y))

        start = pt(curve.start_point)
        pts.append(("move", start))
        for seg in curve:
            if seg.is_corner:
                pts.append(("line", pt(seg.c)))
                pts.append(("line", pt(seg.end_point)))
            else:
                pts.append(("curve", pt(seg.c1), pt(seg.c2), pt(seg.end_point)))
        contours.append(pts)
    return contours


def signed_area(contour):
    pts = []
    for seg in contour:
        pts.extend(seg[1:])
    total = 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        total += x0 * y1 - x1 * y0
    return total / 2.0


def inside(point, contour):
    """Ray-cast test against a contour's on-curve points."""
    x, y = point
    pts = [seg[-1] for seg in contour]
    hit = False
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        if (y0 > y) != (y1 > y):
            xx = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
            if x < xx:
                hit = not hit
    return hit


def orient(contours):
    """TrueType fills non-zero: outer contours clockwise, holes anticlockwise."""
    fixed = []
    for i, c in enumerate(contours):
        probe = c[0][1]
        depth = sum(1 for j, other in enumerate(contours)
                    if j != i and inside(probe, other))
        want_clockwise = (depth % 2 == 0)
        is_clockwise = signed_area(c) < 0
        if is_clockwise != want_clockwise:
            c = reverse_contour(c)
        fixed.append(c)
    return fixed


def reverse_contour(contour):
    """Reverse a contour, keeping its curve segments intact."""
    nodes = [contour[0][1]]
    segs = []
    for seg in contour[1:]:
        if seg[0] == "line":
            segs.append(("line", None, None, seg[1]))
        else:
            segs.append(("curve", seg[1], seg[2], seg[3]))
        nodes.append(seg[-1])

    out = [("move", nodes[-1])]
    for i in range(len(segs) - 1, -1, -1):
        kind, c1, c2, _ = segs[i]
        target = nodes[i]
        if kind == "line":
            out.append(("line", target))
        else:
            out.append(("curve", c2, c1, target))
    return out


def draw(contours, pen, scale, dx, dy):
    def tx(p):
        return (p[0] * scale + dx, p[1] * scale + dy)

    for c in contours:
        pen.moveTo(tx(c[0][1]))
        for seg in c[1:]:
            if seg[0] == "line":
                pen.lineTo(tx(seg[1]))
            else:
                pen.curveTo(tx(seg[1]), tx(seg[2]), tx(seg[3]))
        pen.closePath()


def main():
    img = np.asarray(Image.open(SHEET).convert("L")).astype(int)
    ink = img < INK_MAX_LUMA
    cells = find_digits(ink)

    traced, widths = [], []
    for bmp in cells:
        contours = orient(trace(bmp))
        scale = DIGIT_HEIGHT / float(bmp.shape[0])
        traced.append((contours, scale))
        widths.append(bmp.shape[1] * scale)

    advance = int(round(max(widths) + 2 * SIDE_BEARING))
    print("tabular advance: %d units (%.1f%% of em)" % (advance, 100.0 * advance / UPM))

    order = [".notdef"] + [str(d) for d in range(10)]
    glyphs, metrics = {}, {}

    pen = TTGlyphPen(None)
    glyphs[".notdef"] = pen.glyph()
    metrics[".notdef"] = (advance, 0)

    for digit, (contours, scale) in enumerate(traced):
        tt = TTGlyphPen(None)
        pen = Cu2QuPen(tt, CURVE_ERROR)
        dx = (advance - widths[digit]) / 2.0
        draw(contours, pen, scale, dx, 0)
        glyphs[str(digit)] = tt.glyph()
        metrics[str(digit)] = (advance, int(round(dx)))
        print("  %s  width %3d  bearing %3d" % (digit, round(widths[digit]), round(dx)))

    fb = FontBuilder(UPM, isTTF=True)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap({ord(str(d)): str(d) for d in range(10)})
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics(metrics)

    # centre the digit block in the line box so the clock sits level
    ascent = (UPM + DIGIT_HEIGHT) // 2
    descent = ascent - UPM
    fb.setupHorizontalHeader(ascent=ascent, descent=descent)
    fb.setupNameTable({
        "familyName": FAMILY,
        "styleName": STYLE,
        "psName": FAMILY + "-" + STYLE,
        "fullName": FAMILY,
    })
    fb.setupOS2(sTypoAscender=ascent, sTypoDescender=descent, sTypoLineGap=0,
                usWinAscent=ascent, usWinDescent=-descent,
                sCapHeight=DIGIT_HEIGHT, sxHeight=DIGIT_HEIGHT)
    fb.setupPost()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fb.save(OUT)
    print("wrote", OUT, OUT.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
