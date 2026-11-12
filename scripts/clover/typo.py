"""Text to SVG paths with the vendored fonts (so the pictures look the same everywhere)."""
import os

from fontTools.ttLib import TTFont

_DIR = os.path.join(os.path.dirname(__file__), "fonts")
FONTS = {
    "title": ("Syne.ttf", {"wght": 800}),
    "mono": ("MartianMono.ttf", {"wght": 420, "wdth": 100}),
    "monoB": ("MartianMono.ttf", {"wght": 650, "wdth": 100}),
}
_cache = {}


def _font(kind):
    if kind not in _cache:
        name, loc = FONTS[kind]
        f = TTFont(os.path.join(_DIR, name))
        _cache[kind] = (f.getGlyphSet(location=loc), f.getBestCmap(), f["head"].unitsPerEm)
    return _cache[kind]


def text(s, x, y, size, fill, anchor="start", kind="mono", track=0):
    """Returns (svg path, width). Baseline at y."""
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    gs, cmap, upm = _font(kind)
    k = size / upm
    tr = track * size / 1000
    chars = [c for c in s if ord(c) in cmap]
    total = sum(gs[cmap[ord(c)]].width * k + tr for c in chars) - tr if chars else 0
    x -= total if anchor == "end" else total / 2 if anchor == "middle" else 0
    pen = SVGPathPen(gs)
    for c in chars:
        g = gs[cmap[ord(c)]]
        g.draw(TransformPen(pen, (k, 0, 0, -k, x, y)))
        x += g.width * k + tr
    return f'<path d="{pen.getCommands()}" fill="{fill}"/>', total
