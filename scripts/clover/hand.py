"""Handwriting: Hershey single-stroke glyphs (public domain) drawn with the pen from ink.py,
plus the hand-built 'Bilim' lettering used in the header."""
import json
import math
import os
import random

from ink import INK, brush

_FONTS = json.load(open(os.path.join(os.path.dirname(__file__), "hershey.json")))


def measure(s, size, font="futural", spacing=0.6):
    f = _FONTS[font]
    k = size / (f["base"] - f["cap"])
    return sum((f["g"].get(c, f["g"]["?"])[1] + spacing) * k for c in s)


def write(s, x, y, size, rnd, font="futural", ink=INK, width=None, anchor="start", skew=8, spacing=0.6):
    """Draw text with its baseline at y; size is the cap height in px. Returns (svg, width)."""
    f = _FONTS[font]
    k = size / (f["base"] - f["cap"])
    total = measure(s, size, font, spacing)
    x -= total if anchor == "end" else total / 2 if anchor == "middle" else 0
    width = width or max(1.1, size * 0.11)
    sk = math.tan(math.radians(skew))
    out, cx = [], x
    for c in s:
        left, adv, strokes = f["g"].get(c, f["g"]["?"])
        dy = rnd.uniform(-.06, .06) * size
        sc = rnd.uniform(.96, 1.04)
        for st in strokes:
            pts = []
            for px, py in st:
                gx = (px - left) * k * sc
                gy = (py - f["base"]) * k * sc
                pts.append((cx + gx - gy * sk + rnd.uniform(-.25, .25), y + gy + dy + rnd.uniform(-.25, .25)))
            if len(pts) == 1:
                pts.append((pts[0][0] + .5, pts[0][1] + .5))
            out.append(brush(pts, width, rnd, taper=(.25, .35), wob=.08, fill=ink))
        cx += (adv + spacing) * k
    return "".join(out), total


def bilim(ox, oy, s, seed, ink=INK):
    """Hand-built pen lettering for the name. Returns (svg, [i-dot positions])."""
    rnd = random.Random(seed)
    skew = math.tan(math.radians(13))
    parts = []

    def T(pts, dx, j=1.0):
        return [(ox + ((x + dx + rnd.uniform(-j, j)) - (y + rnd.uniform(-j, j)) * skew) * s, oy + y * s) for x, y in pts]

    def pen(pts, dx, w=7.5, passes=2):
        w *= 1.3
        parts.append(brush(T(pts, dx, .8), w, rnd, taper=(.35, .5), wob=.15, fill=ink))
        for _ in range(passes):
            q = [(x + rnd.uniform(-2.2, 2.2), y + rnd.uniform(-2.2, 2.2)) for x, y in pts]
            parts.append(brush(T(q, dx, 1.5), w * rnd.uniform(.18, .3), rnd, taper=(.4, .4), wob=.1, fill=ink))

    pen([(10, -168), (6, -110), (2, -50), (-2, 6)], 0, 8.5)
    pen([(-18, -150), (20, -170), (66, -166), (84, -138), (62, -104), (16, -92), (54, -94), (94, -70), (98, -30),
         (70, -4), (24, 4), (-8, -4)], 0, 7)
    pen([(4, -86), (0, -44), (-1, -8), (10, 3), (26, -6)], 128, 7)
    pen([(-6, -40), (20, -120), (30, -172), (16, -182), (4, -150), (0, -70), (0, -10), (12, 3), (30, -6)], 168, 7)
    pen([(4, -86), (0, -44), (-1, -8), (10, 3), (26, -6)], 226, 7)
    pen([(0, -84), (2, -40), (0, 2), (4, -50), (20, -84), (40, -86), (48, -60), (46, -20), (46, 2),
         (50, -54), (66, -86), (88, -86), (96, -60), (94, -18), (100, 2), (118, -6)], 276, 7)
    dots = [T([(8, -116)], 128)[0], T([(8, -116)], 226)[0]]
    parts.append(brush(T([(-20, 30), (80, 22), (220, 22), (360, 12), (420, 8)], 0), 3.2, rnd, taper=(.1, .6), fill=ink))
    parts.append(brush(T([(40, 36), (200, 30), (330, 24)], 0), 1.2, rnd, taper=(.3, .5), fill=ink))
    return "".join(parts), dots
