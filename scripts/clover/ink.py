"""Ink-on-paper drawing primitives. Everything returns SVG fragments as strings."""
import math
import random

PAPER = "#fbfaf6"
INK = "#141414"
LUCK_WASH, LUCK_EDGE, LUCK_HATCH = "#9dcb93", "#72a66c", "#5a8c5b"
AUTUMN = "#ddb36f"

STYLE = """<style>
      .sway { animation: sway ease-in-out infinite alternate; }
      @keyframes sway { from { transform: rotate(-4deg); } to { transform: rotate(4deg); } }
      .twinkle { transform-box: fill-box; transform-origin: center; animation: tw ease-in-out infinite; }
      @keyframes tw { 0%,100% { transform: scale(.55); opacity:.35; } 50% { transform: scale(1); opacity:1; } }
      .soft { transform-box: fill-box; transform-origin: center; animation: soft ease-in-out infinite; }
      @keyframes soft { 0%,100% { transform: scale(.85) rotate(-8deg); } 50% { transform: scale(1.05) rotate(8deg); } }
      .rays { animation: rays 3.2s ease-in-out infinite; }
      @keyframes rays { 0%,100% { opacity:.35; } 50% { opacity:.9; } }
      .halo { transform-box: fill-box; transform-origin: center; animation: halo 3.2s ease-in-out infinite; }
      @keyframes halo { 0%,100% { opacity:.65; transform: scale(.96); } 50% { opacity:1; transform: scale(1.04); } }
      .bob { animation: bob 4.5s ease-in-out infinite alternate; }
      @keyframes bob { from { transform: translateY(-4px); } to { transform: translateY(4px); } }
      .fall { animation: fall linear infinite; }
      @keyframes fall { from { transform: translate(0,0) rotate(0deg); } to { transform: translate(var(--dx),var(--dy)) rotate(var(--r)); } }
      .fly { animation: fly 14s ease-in-out infinite; }
      @keyframes fly { 0% { transform: translate(0,0); } 25% { transform: translate(140px,-30px); } 50% { transform: translate(260px,10px); }
                       75% { transform: translate(120px,30px); } 100% { transform: translate(0,0); } }
      .buzz { transform-box: fill-box; transform-origin: center; animation: buzz .18s linear infinite alternate; }
      @keyframes buzz { from { transform: scaleY(1); } to { transform: scaleY(.5); } }
      @media (prefers-reduced-motion: reduce) { * { animation: none !important; } }
    </style>"""

FILTERS = """<filter id="wash" x="-50%" y="-50%" width="200%" height="200%">
      <feTurbulence type="fractalNoise" baseFrequency=".035" numOctaves="2" seed="3" result="n"/>
      <feDisplacementMap in="SourceGraphic" in2="n" scale="40" result="d"/>
      <feGaussianBlur in="d" stdDeviation="14"/>
    </filter>
    <filter id="wc" x="-10%" y="-10%" width="120%" height="120%">
      <feTurbulence type="fractalNoise" baseFrequency=".05" numOctaves="3" seed="2" result="n"/>
      <feDisplacementMap in="SourceGraphic" in2="n" scale="7" result="d"/>
      <feGaussianBlur in="d" stdDeviation=".7"/>
    </filter>
    <filter id="grain" x="0" y="0" width="100%" height="100%">
      <feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="8" stitchTiles="stitch"/>
      <feColorMatrix values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1.4 -.6"/>
    </filter>"""


# ------------------------------------------------------------------ geometry
def d(pts, close=True):
    s = "M" + " ".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    return s + ("Z" if close else "")


def wobble(rnd, amp):
    ph = [rnd.uniform(0, 6.28) for _ in range(4)]
    return lambda t: sum(amp / (i + 1) * math.sin((i + 2) * t + ph[i]) for i in range(4))


def rot(pts, deg, ox=0.0, oy=0.0):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return [(ox + x * c - y * s, oy + x * s + y * c) for x, y in pts]


def line_pts(p0, p1, rnd, amp=0.8, n=24, bow=0.0):
    w = wobble(rnd, amp)
    (x0, y0), (x1, y1) = p0, p1
    nx, ny = -(y1 - y0), x1 - x0
    ln = math.hypot(nx, ny) or 1
    nx, ny = nx / ln, ny / ln
    out = []
    for i in range(n + 1):
        t = i / n
        off = w(t * 6) + bow * math.sin(math.pi * t)
        out.append((x0 + (x1 - x0) * t + nx * off, y0 + (y1 - y0) * t + ny * off))
    return out


def catmull(pts, n=10):
    if len(pts) < 3:
        return list(pts)
    out, P = [], [pts[0]] + list(pts) + [pts[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for j in range(n):
            t = j / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * (2 * p1[k] + (-p0[k] + p2[k]) * t + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t2
                                    + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t3) for k in (0, 1)))
    out.append(pts[-1])
    return out


def brush(pts, width, rnd, taper=(0.35, 0.5), wob=0.15, fill=INK, smooth=True):
    """A pen stroke with pressure: thin tails, thicker middle."""
    c = catmull(pts) if smooth else list(pts)
    n = len(c)
    if n < 2:
        return ""
    w = wobble(rnd, wob)
    L, R = [], []
    for i in range(n):
        t = i / (n - 1)
        a, b = c[max(i - 1, 0)], c[min(i + 1, n - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(dx, dy) or 1
        nx, ny = -dy / ln, dx / ln
        k = min(1, 0.25 + t / taper[0] * 0.75, 0.2 + (1 - t) / taper[1] * 0.8)
        hw = width / 2 * k * (1 + 0.12 * math.sin(t * 9 + rnd.random()))
        o = w(t * 6) * 0.3
        L.append((c[i][0] + nx * (hw + o), c[i][1] + ny * (hw + o)))
        R.append((c[i][0] - nx * hw, c[i][1] - ny * hw))
    return f'<path d="{d(L + R[::-1])}" fill="{fill}"/>'


def leaf_pts(L, rnd, amp=1.1, n=56):
    """Heart-shaped leaflet with its point at the origin, lobes pointing up, length ~L."""
    k = L / 29.0
    wx, wy = wobble(rnd, amp), wobble(rnd, amp)
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x = 16 * math.sin(t) ** 3 * 0.86
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)) - 17
        pts.append((x * k + wx(t), y * k + wy(t)))
    return pts


# ------------------------------------------------------------------ doodles
def _anim(cls, dur, rnd):
    return f'class="{cls}" style="animation-duration:{dur:.1f}s;animation-delay:{-rnd.uniform(0, dur):.1f}s"'


def star5(cx, cy, r, rnd, sw=1.6, fill="none", ink=INK, cls="twinkle", dur=3.0):
    rot0 = rnd.uniform(-20, 20)
    pts = []
    for i in range(10):
        a = math.radians(rot0 - 90 + i * 36)
        rr = (r if i % 2 == 0 else r * 0.45) * rnd.uniform(0.9, 1.1)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    body = f'<path d="{d(pts)}" fill="{fill}" stroke="{ink}" stroke-width="{sw}" stroke-linejoin="round"/>'
    return f'<g {_anim(cls, dur, rnd)}>{body}</g>' if cls else body


def sparkle(cx, cy, r, rnd, fill=INK, cls="twinkle", dur=2.6):
    k = r * 0.18
    body = (f'<path d="M{cx:.1f} {cy-r:.1f} Q{cx+k:.1f} {cy-k:.1f} {cx+r:.1f} {cy:.1f} Q{cx+k:.1f} {cy+k:.1f} {cx:.1f} {cy+r:.1f} '
            f'Q{cx-k:.1f} {cy+k:.1f} {cx-r:.1f} {cy:.1f} Q{cx-k:.1f} {cy-k:.1f} {cx:.1f} {cy-r:.1f}Z" fill="{fill}"/>')
    return f'<g {_anim(cls, dur, rnd)}>{body}</g>' if cls else body


def ink_clover(cx, cy, L, leaves, rnd, ink=INK, paper=PAPER, solid=False, sw=2.0, angle=0.0, tint=None):
    """Meadow clover: outlined (paper fill), solid ink, or with a colour wash (tint)."""
    out = []
    for i in range(leaves):
        a = angle + i * 360 / leaves + (45 if leaves == 4 else 0) + rnd.uniform(-8, 8)
        Li = L * rnd.uniform(0.88, 1.05)
        pts = rot(leaf_pts(Li, rnd, 0.7), a, cx, cy)
        if tint:
            cp = rot(leaf_pts(Li * 0.97, rnd, 1.3), a, cx + 2, cy + 1.5)
            out.append(f'<path d="{d(pts)}" fill="{paper}"/><path d="{d(cp)}" fill="{tint}" opacity=".75"/>')
        fill = ink if solid else ("none" if tint else paper)
        out.append(f'<path d="{d(pts)}" fill="{fill}" stroke="{ink}" stroke-width="{sw}" stroke-linejoin="round"/>')
        k = Li / 29
        vein = line_pts((0, -3), (0, -20 * k), rnd, .4, 8)
        out.append(f'<path d="{d(rot(vein, a, cx, cy), False)}" fill="none" stroke="{paper if solid else ink}" '
                   f'stroke-width="{sw * .6:.1f}" stroke-linecap="round" opacity="{.9 if solid else .55}"/>')
    return "".join(out)


def watercolour_clover(cx, cy, L, leaves, rnd, uid, fill_leaves=None, sw=1.8, angle=-6.0, styles=None):
    """The soft 'lucky' clover: watercolour wash, pencil hatching, broken outline.
    fill_leaves: how many leaves get the wash (float allowed: the remainder leaf is hatched only).
    styles: optional per-leaf list of ('wash'|'hatch'|'dots'|'empty', length_factor)."""
    out = []
    n_fill = leaves if fill_leaves is None else fill_leaves
    for i in range(leaves):
        a = angle + 45 * (leaves == 4) + i * 360 / leaves + rnd.uniform(-9, 9)
        style, lf = styles[i] if styles else (("wash" if i < int(n_fill) else ("hatch" if i < n_fill else "empty")), 1.0)
        Li = L * lf * rnd.uniform(0.9, 1.04)
        shape = rot(leaf_pts(Li, rnd, 1.5), a, cx, cy)
        cid = f"{uid}{i}"
        out.append(f'<clipPath id="{cid}"><path d="{d(shape)}"/></clipPath>')
        if style == "wash":
            wash = rot(leaf_pts(Li * .97, rnd, 2.2), a, cx + 2, cy + 2)
            out.append(f'<path d="{d(wash)}" fill="{LUCK_WASH}" stroke="{LUCK_EDGE}" stroke-width="2.5" '
                       f'stroke-opacity=".5" filter="url(#wc)" opacity=".9"/>')
        if style in ("wash", "hatch"):
            hs = []
            for k in range(-14, 15):
                off = k * (6.5 if style == "wash" else 4.5)
                hs.append(f'<path d="{d(line_pts((cx - 100 + off, cy - 100 - off), (cx + 100 + off, cy + 100 - off), rnd, .5, 16), False)}"/>')
            op = .38 if style == "wash" else .7
            out.append(f'<g clip-path="url(#{cid})" stroke="{LUCK_HATCH}" stroke-width=".8" opacity="{op}" fill="none">{"".join(hs)}</g>')
        if style == "dots":
            dots = []
            for _ in range(int(Li * 1.6)):
                x, y = cx + rnd.uniform(-Li, Li), cy + rnd.uniform(-Li, Li)
                dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rnd.uniform(.9, 1.5):.1f}"/>')
            out.append(f'<g clip-path="url(#{cid})" fill="{LUCK_HATCH}" opacity=".75">{"".join(dots)}</g>')
        n = len(shape)
        st = rnd.randrange(n)
        seg = [shape[(st + j) % n] for j in range(int(n * rnd.uniform(.84, .94)))]
        out.append(f'<path d="{d(seg, False)}" fill="none" stroke="{INK}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"/>')
        st2 = rnd.randrange(n)
        seg2 = [(x + rnd.uniform(-.8, .8), y + rnd.uniform(-.8, .8)) for x, y in (shape[(st2 + j) % n] for j in range(int(n * .45)))]
        out.append(f'<path d="{d(seg2, False)}" fill="none" stroke="{INK}" stroke-width=".8" opacity=".5" stroke-linecap="round"/>')
        k_ = Li / 29
        vein = line_pts((0, -4), (0, -19 * k_), rnd, .5, 10, rnd.uniform(-1.5, 1.5))
        out.append(f'<path d="{d(rot(vein, a, cx, cy), False)}" fill="none" stroke="{INK}" stroke-width=".9" opacity=".45" stroke-linecap="round"/>')
    return "".join(out)


def glow(cx, cy, rnd, rx=120, ry=104, ticks=True):
    out = [f'<ellipse cx="{cx + 6}" cy="{cy - 4}" rx="{rx}" ry="{ry}" fill="#dcebc9" filter="url(#wash)" class="halo"/>']
    if ticks:
        t = []
        for ang, r0, ln in [(-62, 112, 18), (-50, 118, 12), (-128, 108, 14), (20, 116, 16), (32, 110, 10), (160, 114, 12)]:
            a = math.radians(ang)
            k = rx / 120
            p0 = (cx + r0 * k * math.cos(a), cy + r0 * k * math.sin(a))
            p1 = (cx + (r0 + ln) * k * math.cos(a), cy + (r0 + ln) * k * math.sin(a))
            t.append(f'<path d="{d(line_pts(p0, p1, rnd, .3, 6, rnd.uniform(-2, 2)), False)}" fill="none" stroke="{INK}" '
                     f'stroke-width="1.4" stroke-linecap="round" opacity=".8"/>')
        out.append(f'<g class="rays">{"".join(t)}</g>')
    return "".join(out)


# ------------------------------------------------------------------ meadow + seasons
def flower_head(cx, cy, r, rnd, ink=INK, paper=PAPER):
    """White clover flower: a pom-pom of small florets."""
    out = [f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{paper}"/>']
    for i in range(16):
        a = math.radians(i * 22.5 + rnd.uniform(-8, 8))
        rr = r * rnd.uniform(.55, 1.0)
        x1, y1 = cx + rr * math.cos(a), cy + rr * math.sin(a)
        x0, y0 = cx + rr * .35 * math.cos(a), cy + rr * .35 * math.sin(a)
        out.append(f'<path d="M{x0:.1f} {y0:.1f} L{x1:.1f} {y1:.1f}" stroke="{ink}" stroke-width=".9" stroke-linecap="round"/>')
    blob = [(cx + r * rnd.uniform(.9, 1.1) * math.cos(t / 10 * math.tau), cy + r * rnd.uniform(.9, 1.1) * math.sin(t / 10 * math.tau)) for t in range(10)]
    out.append(f'<path d="{d(catmull(blob + blob[:1], 4))}" fill="none" stroke="{ink}" stroke-width="1.2"/>')
    return "".join(out)


def snow_cap(cx, cy, w, rnd, ink=INK):
    pts = [(cx - w / 2, cy)]
    for i in range(1, 6):
        pts.append((cx - w / 2 + w * i / 6, cy - rnd.uniform(3, 7)))
    pts.append((cx + w / 2, cy))
    sm = catmull(pts, 4)
    return f'<path d="{d(sm)}" fill="#ffffff" stroke="{ink}" stroke-width="1.2" stroke-linejoin="round"/>'


def meadow(W, base, n, seed, scale, season="summer", ink=INK, paper=PAPER, solid_p=0.3, sw=1.8):
    rnd = random.Random(seed)
    out = []
    flower_p = {"spring": .18, "summer": .28}.get(season, 0)
    autumn_p = .2 if season == "autumn" else 0
    for i in range(n):
        x = (i + rnd.uniform(0.1, 0.9)) * W / n
        s = rnd.uniform(*scale)
        h = rnd.uniform(16, 50) * s / 14 * (0.7 if season == "winter" else 1.15 if season == "summer" else 1)
        bend = rnd.uniform(-10, 10)
        dur = rnd.uniform(4.5, 7.5)
        tip = (x + bend * .3, base - h)
        stem = line_pts((x, base), tip, rnd, .5, 12, bend * .4)
        g = f'<path d="{d(stem, False)}" fill="none" stroke="{ink}" stroke-width="{sw}" stroke-linecap="round"/>'
        if rnd.random() < flower_p:
            g += flower_head(tip[0], tip[1] - s * .3, s * .75, rnd, ink, paper)
        else:
            tint = AUTUMN if rnd.random() < autumn_p else None
            g += ink_clover(tip[0], tip[1], s, 3, rnd, ink, paper, solid=(not tint and rnd.random() < solid_p),
                            sw=sw, angle=rnd.uniform(-30, 30), tint=tint)
            if season == "winter" and rnd.random() < .55:
                g += snow_cap(tip[0], tip[1] - s * 1.0, s * 1.6, rnd, ink)
        out.append(f'<g class="sway" style="animation-duration:{dur:.1f}s;animation-delay:{-rnd.uniform(0, dur):.1f}s;'
                   f'transform-origin:{x:.0f}px {base}px">{g}</g>')
    return "".join(out)


def snowdrift(W, base, rnd, ink=INK):
    pts = [(-10, base + 20)]
    for i in range(0, 25):
        pts.append((i * W / 24, base - rnd.uniform(22, 40)))
    pts.append((W + 10, base + 20))
    sm = catmull(pts, 6)
    return f'<path d="{d(sm)}" fill="#ffffff" stroke="{ink}" stroke-width="1.6" stroke-linejoin="round"/>'


def falling(W, H, rnd, kind, n, ink=INK):
    """Falling snowflakes or autumn leaflets."""
    out = []
    for _ in range(n):
        x, y = rnd.uniform(0, W), rnd.uniform(-60, H * .5)
        dur = rnd.uniform(9, 16)
        dx, dy, r = rnd.uniform(-60, 60), H - y + 40, rnd.choice([-1, 1]) * rnd.uniform(180, 540)
        if kind == "snow":
            s = rnd.uniform(2, 4)
            body = (f'<g stroke="{ink}" stroke-width="1" stroke-linecap="round">'
                    + "".join(f'<path d="M{x - s * math.cos(a):.1f} {y - s * math.sin(a):.1f} L{x + s * math.cos(a):.1f} {y + s * math.sin(a):.1f}"/>'
                              for a in (0, 1.05, 2.1)) + '</g>')
        else:
            pts = rot(leaf_pts(rnd.uniform(7, 10), rnd, .3, 24), rnd.uniform(0, 360), x, y)
            body = (f'<path d="{d(pts)}" fill="{AUTUMN}" opacity=".8"/>'
                    f'<path d="{d(pts)}" fill="none" stroke="{ink}" stroke-width="1"/>')
        out.append(f'<g class="fall" style="--dx:{dx:.0f}px;--dy:{dy:.0f}px;--r:{r:.0f}deg;transform-origin:{x:.0f}px {y:.0f}px;'
                   f'transform-box:view-box;animation-duration:{dur:.1f}s;animation-delay:{-rnd.uniform(0, dur):.1f}s">{body}</g>')
    return "".join(out)


def bee(x, y, rnd, ink=INK, scale=1.6):
    body = (f'<ellipse cx="{x}" cy="{y}" rx="7" ry="5" fill="#f2d07a" stroke="{ink}" stroke-width="1.3"/>'
            f'<path d="M{x - 2} {y - 5} Q{x - 3} {y} {x - 2} {y + 5} M{x + 2} {y - 5} Q{x + 1} {y} {x + 2} {y + 5}" stroke="{ink}" stroke-width="1.4" fill="none"/>'
            f'<g class="buzz"><ellipse cx="{x - 2}" cy="{y - 8}" rx="4" ry="5" fill="#fff" stroke="{ink}" stroke-width="1"/>'
            f'<ellipse cx="{x + 3}" cy="{y - 8}" rx="4" ry="5" fill="#fff" stroke="{ink}" stroke-width="1"/></g>')
    trail = line_pts((x - 60, y + 8), (x - 12, y + 2), rnd, 2, 20, 6)
    return (f'<g class="fly"><g transform="translate({x} {y}) scale({scale}) translate({-x} {-y})">'
            f'<path d="{d(trail, False)}" fill="none" stroke="{ink}" stroke-width="1" stroke-dasharray="3 4" opacity=".6"/>{body}</g></g>')


def season_of(month):
    return {12: "winter", 1: "winter", 2: "winter", 3: "spring", 4: "spring", 5: "spring",
            6: "summer", 7: "summer", 8: "summer"}.get(month, "autumn")
