"""The floating island: an isometric voxel world that reacts to your GitHub/WakaTime activity.

What drives what:
  season (month)            -> materials: grass, crowns, roofs, flowers, falling petals/leaves/snow
  phase (Bishkek hour)      -> sky palette, night overlay, lit windows, stars, fireflies
  commits this week         -> weather: sun (+ rainbow), clouds, rain / snow
  total commits             -> island growth: new buildings unlock every few hundred commits
  WakaTime languages        -> districts: TypeScript forest, Python lake (+ waterfall), C++ cliffs, other = meadow
  lucky days                -> the clover garden on the islet (one clover per lucky day)
  date                      -> holidays (New Year, Nooruz, Halloween)
  date + phase hash         -> rare events: shooting star, aurora, a cat on the bench, rainbow
"""
import hashlib
import math
import random

from ink import leaf_pts
from typo import text

INK = "#2b2540"

SEASONS = {
    "winter": dict(top="#fbfcff", top2="#eef2fb", side=("#b9c0d8", "#9ea6c4"), leaf="#9fd3a8", crown="#f4f7fd",
                   roof="#f7f9fc", flower="#ffffff", water="#a9c8e6", fall="snow", tag="snow on the ground"),
    "spring": dict(top="#a9d8a0", top2="#f5b8ca", side=("#d7b49c", "#c19a80"), leaf="#7cc68c", crown="#f5b8ca",
                   roof="#e98d8d", flower="#f5a9bf", water="#9fd0ec", fall="petals", tag="blossom"),
    "summer": dict(top="#8fcf7c", top2="#b6e08f", side=("#d9b391", "#c39876"), leaf="#5fb36f", crown="#5fb36f",
                   roof="#e07a5f", flower="#ffd884", water="#7cc3ea", fall=None, tag="summer"),
    "autumn": dict(top="#e7a85d", top2="#d9874b", side=("#c99272", "#ad775c"), leaf="#7cc68c", crown="#f0c06a",
                   roof="#c9653f", flower="#e7a85d", water="#9cc6e4", fall="leaves", tag="falling leaves"),
}
SKY = {
    "morning": ("#f9d9c4", "#f1e4ef"),
    "day": None,  # season-specific, below
    "evening": ("#f2b38f", "#b39ad1"),
    "night": ("#161b36", "#3a3b6b"),
}
DAY_SKY = {"winter": ("#dfe6f4", "#c8cfe8"), "spring": ("#fbe3ea", "#dfe9f6"), "summer": ("#d3eef4", "#f8e7c4"), "autumn": ("#f6d9c7", "#e6c6dc")}
STONE = ("#f3ece4", "#ddd1c4", "#c5b6a6")
LANG_COL = ["#7cc68c", "#8fb8de", "#c9b8a6", "#f0c06a"]
DISTRICT = ["forest", "lake", "cliffs", "meadow"]

# island growth: (commits needed, what appears)
UNLOCKS = [(0, "hut"), (100, "tree"), (300, "waterfall"), (500, "islet"), (800, "windmill"), (1200, "second hut"),
           (1600, "lighthouse"), (2000, "balloon"), (2500, "observatory"), (3500, "second islet"), (5000, "castle")]


def shade(hex_, f):
    c = [int(hex_[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{max(0, min(255, round(v * f))):02x}" for v in c)


def mix(a, b, t):
    a = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


def chance(key, odds):
    return int(hashlib.sha256(key.encode()).hexdigest(), 16) % odds == 0


def poly(pts):
    return "M" + " L".join(f"{a:.1f} {b:.1f}" for a, b in pts) + "Z"


# ---------------------------------------------------------------- iso engine
class Iso:
    def __init__(self, ox, oy, s):
        self.ox, self.oy, self.s = ox, oy, s
        self.cubes = {}
        self.extra = {}

    def P(self, x, y, z):
        return self.ox + (x - y) * self.s, self.oy + (x + y) * self.s / 2 - z * self.s

    def add(self, x, y, z, top, left=None, right=None):
        self.cubes[(x, y, z)] = (top, left or shade(top, .86), right or shade(top, .74))

    def put(self, key, markup):
        self.extra[key] = self.extra.get(key, "") + markup

    def face(self, x, y, z, f, u0, v0, u1, v1):
        P = self.P
        if f == "top":
            pts = [P(x + u0, y + v0, z + 1), P(x + u1, y + v0, z + 1), P(x + u1, y + v1, z + 1), P(x + u0, y + v1, z + 1)]
        elif f == "px":
            pts = [P(x + 1, y + u0, z + v0), P(x + 1, y + u1, z + v0), P(x + 1, y + u1, z + v1), P(x + 1, y + u0, z + v1)]
        else:
            pts = [P(x + u0, y + 1, z + v0), P(x + u1, y + 1, z + v0), P(x + u1, y + 1, z + v1), P(x + u0, y + 1, z + v1)]
        return poly(pts)

    def render(self):
        out = []
        for (x, y, z) in sorted(self.cubes, key=lambda c: (c[0] + c[1], c[2])):
            top, left, right = self.cubes[(x, y, z)]
            P = self.P
            if (x, y, z + 1) not in self.cubes:
                out.append(f'<path d="{poly([P(x, y, z + 1), P(x + 1, y, z + 1), P(x + 1, y + 1, z + 1), P(x, y + 1, z + 1)])}" fill="{top}"/>')
            if (x, y + 1, z) not in self.cubes:
                out.append(f'<path d="{poly([P(x, y + 1, z), P(x + 1, y + 1, z), P(x + 1, y + 1, z + 1), P(x, y + 1, z + 1)])}" fill="{left}"/>')
            if (x + 1, y, z) not in self.cubes:
                out.append(f'<path d="{poly([P(x + 1, y, z), P(x + 1, y + 1, z), P(x + 1, y + 1, z + 1), P(x + 1, y, z + 1)])}" fill="{right}"/>')
            if (x, y, z) in self.extra:
                out.append(self.extra[(x, y, z)])
        return "".join(out)

    def flat_clover(self, cx, cy, z, L, fill, leaves=4):
        rnd = random.Random(3)
        out = []
        for i in range(leaves):
            a = math.radians(i * 360 / leaves + (45 if leaves == 4 else 0))
            pts = leaf_pts(L, rnd, 0, 40)
            ca, sa = math.cos(a), math.sin(a)
            out.append(f'<path d="{poly([self.P(cx + px * ca - py * sa, cy + px * sa + py * ca, z) for px, py in pts])}" '
                       f'fill="{fill}" stroke="{shade(fill, .7)}" stroke-width="1.2"/>')
        return "".join(out)


def standing_clover(cx, cy, L, col, leaves=4, stem=40):
    rr = random.Random(5)
    out = [f'<path d="M{cx:.1f} {cy:.1f} q-3 {-stem / 2:.1f} 0 {-stem:.1f}" stroke="{shade(col, .6)}" stroke-width="2.2" fill="none" stroke-linecap="round"/>']
    for i in range(leaves):
        a = math.radians(i * 360 / leaves + (45 if leaves == 4 else 0))
        pts = [(cx + px * math.cos(a) - py * math.sin(a), cy - stem + (px * math.sin(a) + py * math.cos(a)) * .8) for px, py in leaf_pts(L, rr, 0, 36)]
        out.append(f'<path d="{poly(pts)}" fill="{col}" stroke="{shade(col, .65)}" stroke-width="1.2"/>')
    return "".join(out)


def sparkle(x, y, r, delay=0, fill="#fffbe6"):
    q = r * .2
    return (f'<path d="M{x:.1f} {y - r:.1f} Q{x + q:.1f} {y - q:.1f} {x + r:.1f} {y:.1f} Q{x + q:.1f} {y + q:.1f} {x:.1f} {y + r:.1f} '
            f'Q{x - q:.1f} {y + q:.1f} {x - r:.1f} {y:.1f} Q{x - q:.1f} {y - q:.1f} {x:.1f} {y - r:.1f}Z" fill="{fill}" class="tw" style="animation-delay:{delay:.1f}s"/>')


STYLE = """<style>
  .bob { animation: bob 5s ease-in-out infinite alternate; } @keyframes bob { from { transform: translateY(-5px); } to { transform: translateY(5px); } }
  .bob2 { animation: bob 7s ease-in-out infinite alternate-reverse; }
  .fall { animation: fall linear infinite; } @keyframes fall { from { transform: translate(0,0) rotate(0deg); } to { transform: translate(var(--dx),var(--dy)) rotate(var(--r)); } }
  .rain { animation: rain .7s linear infinite; } @keyframes rain { from { transform: translate(0,0); } to { transform: translate(-14px,60px); } }
  .drift { animation: drift 40s ease-in-out infinite alternate; } @keyframes drift { from { transform: translateX(-40px); } to { transform: translateX(40px); } }
  .glow { animation: glow 4s ease-in-out infinite; } @keyframes glow { 0%,100% { opacity: .55; } 50% { opacity: 1; } }
  .tw { transform-box: fill-box; transform-origin: center; animation: tw 2.2s ease-in-out infinite; } @keyframes tw { 0%,100% { transform: scale(.5); opacity: .35; } 50% { transform: scale(1.1); opacity: 1; } }
  .pour { animation: pour .9s linear infinite; } @keyframes pour { to { stroke-dashoffset: -28; } }
  .vine { transform-box: fill-box; transform-origin: top; animation: vine 4s ease-in-out infinite alternate; } @keyframes vine { from { transform: rotate(-5deg); } to { transform: rotate(5deg); } }
  .bird { animation: bird 16s ease-in-out infinite; } @keyframes bird { 50% { transform: translate(60px,-14px); } }
  .spin { transform-box: fill-box; transform-origin: center; animation: spin 6s linear infinite; } @keyframes spin { to { transform: rotate(360deg); } }
  .whale { animation: whale 16s ease-in-out infinite alternate; } @keyframes whale { from { transform: translate(14px, 6px); } to { transform: translate(-26px, -10px); } }
  .fluke { animation: fluke 3.4s ease-in-out infinite alternate; } @keyframes fluke { from { transform: rotate(-7deg); } to { transform: rotate(7deg); } }
  .fin { animation: fluke 2.6s ease-in-out infinite alternate-reverse; }
  .spout { transform-box: fill-box; transform-origin: center; animation: spout 5s ease-out infinite; opacity: 0; } @keyframes spout { 0% { transform: translate(0,0) scale(.3); opacity: 0; } 10% { opacity: .9; } 40% { transform: translate(-4px,-22px) scale(1.4); opacity: 0; } 100% { opacity: 0; } }
  .drip { animation: drip 4s ease-in infinite; } @keyframes drip { 0%, 60% { transform: translateY(0); opacity: 0; } 65% { opacity: 1; } 100% { transform: translateY(60px); opacity: 0; } }
  .blink { transform-box: fill-box; transform-origin: center; animation: blink 5s infinite; } @keyframes blink { 0%, 90%, 96%, 100% { transform: scaleY(1); } 93% { transform: scaleY(.08); } }
  .flap { transform-box: fill-box; transform-origin: center; animation: flap .22s ease-in-out infinite alternate; } @keyframes flap { to { transform: scaleX(.25); } }
  .bounce { animation: bounce 1.1s cubic-bezier(.5,0,.5,1) infinite alternate; } @keyframes bounce { to { transform: translateY(-22px); } }
  .hop { animation: hop 3.2s ease-in-out infinite; } @keyframes hop { 0%, 70%, 100% { transform: translate(0,0); } 76% { transform: translate(-6px,-9px); } 82% { transform: translate(-12px,0); } 88% { transform: translate(-6px,-7px); } 94% { transform: translate(0,0); } }
  .wag { animation: wag .45s ease-in-out infinite alternate; } @keyframes wag { from { transform: rotate(-16deg); } to { transform: rotate(16deg); } }
  .zz { animation: zz 3s ease-out infinite; opacity: 0; } @keyframes zz { 0% { transform: translate(0,0); opacity: 0; } 20% { opacity: 1; } 100% { transform: translate(10px,-26px); opacity: 0; } }
  .breathe { transform-box: fill-box; transform-origin: bottom; animation: breathe 3.2s ease-in-out infinite; } @keyframes breathe { 50% { transform: scaleY(1.06); } }
  .hover { animation: hover 2.6s ease-in-out infinite alternate; } @keyframes hover { from { transform: translateY(0); } to { transform: translateY(-8px); } }
  .beam { transform-box: view-box; animation: beam 6s ease-in-out infinite alternate; } @keyframes beam { from { opacity: .15; } to { opacity: .6; } }
  .fly { animation: fly 9s ease-in-out infinite alternate; } @keyframes fly { from { transform: translate(-10px,6px); } to { transform: translate(14px,-8px); } }
  .star { stroke-dasharray: 0 300; animation: star 9s ease-in infinite; }
  @keyframes star { 0%, 80% { stroke-dasharray: 0 300; stroke-dashoffset: 0; opacity: 0; } 82% { opacity: 1; } 92% { stroke-dasharray: 70 300; stroke-dashoffset: -110; } 100% { stroke-dasharray: 0 300; stroke-dashoffset: -220; opacity: 0; } }
  .aurora { animation: aur 12s ease-in-out infinite alternate; } @keyframes aur { from { opacity: .25; transform: translateX(-20px); } to { opacity: .7; transform: translateX(20px); } }
  .rise { transform-box: fill-box; transform-origin: bottom; animation: rise 1.8s cubic-bezier(.2,.8,.2,1) both; } @keyframes rise { from { transform: scaleY(0); } }
  .sway2 { transform-box: fill-box; transform-origin: bottom; animation: sway2 3.5s ease-in-out infinite alternate; } @keyframes sway2 { from { transform: rotate(-6deg); } to { transform: rotate(6deg); } }
  @media (prefers-reduced-motion: reduce) { * { animation: none !important; } .star { display: none; } }
</style>"""


def svg(W, H, body, label, sky):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{label}">'
            f'<defs>{STYLE}<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{sky[0]}"/><stop offset="1" stop-color="{sky[1]}"/></linearGradient>'
            f'<radialGradient id="halo"><stop offset="0" stop-color="#ffffff" stop-opacity=".9"/><stop offset="1" stop-color="#ffffff" stop-opacity="0"/></radialGradient>'
            f'<radialGradient id="warm"><stop offset="0" stop-color="#ffd98a" stop-opacity=".8"/><stop offset="1" stop-color="#ffd98a" stop-opacity="0"/></radialGradient>'
            f'<clipPath id="cl"><rect width="{W}" height="{H}" rx="18"/></clipPath></defs>'
            f'<g clip-path="url(#cl)"><rect width="{W}" height="{H}" fill="url(#bg)"/>{body}</g></svg>')


# ---------------------------------------------------------------- state
def make_state(today, phase, season, stats, waka, weekly, latest_repo, lucky_today, found):
    commits = stats["commits"]
    if weekly >= 25:
        weather = "sunny"
    elif weekly >= 8:
        weather = "clear"
    elif weekly >= 1:
        weather = "cloudy"
    else:
        weather = "rain"
    md = (today.month, today.day)
    holiday = None
    if md >= (12, 24) or md <= (1, 7):
        holiday = "new year"
    elif (3, 19) <= md <= (3, 23):
        holiday = "nooruz"
    elif (10, 28) <= md <= (11, 1):
        holiday = "halloween"
    key = f"{today.isoformat()}:{phase}"
    rare = set()
    if phase == "night" and chance(key + "star", 4):
        rare.add("shooting star")
    if phase == "night" and season == "winter" and chance(key + "aurora", 3):
        rare.add("aurora")
    if chance(key + "cat", 6):
        rare.add("cat")
    if weather == "sunny" and phase != "night" and chance(key + "rainbow", 2):
        rare.add("rainbow")
    unlocked = [name for need, name in UNLOCKS if commits >= need]
    nxt = next(((need, name) for need, name in UNLOCKS if commits < need), None)
    langs = []
    for l in waka["languages"]:
        if len(langs) < 3:
            langs.append((l["name"], l["percent"], l.get("hours", 0)))
    rest = waka["languages"][3:]
    if rest:
        langs.append(("Other", sum(l["percent"] for l in rest), sum(l.get("hours", 0) for l in rest)))
    return dict(today=today, phase=phase, season=season, stats=stats, weekly=weekly, weather=weather, holiday=holiday,
                rare=rare, unlocked=unlocked, next=nxt, langs=langs, total=waka.get("total", ""), wrange=waka.get("range", "last 30 days"), all_time=waka.get("all_time", ""), repo=latest_repo,
                lucky=lucky_today, found=found, level=commits // 100)


def sky_colors(st):
    sky = SKY[st["phase"]] or DAY_SKY[st["season"]]
    if st["weather"] in ("cloudy", "rain") and st["phase"] != "night":
        sky = (mix(sky[0], "#9aa3b5", .45 if st["weather"] == "rain" else .25), mix(sky[1], "#9aa3b5", .45 if st["weather"] == "rain" else .25))
    return sky


# ---------------------------------------------------------------- the island
def build_island(st, ox=860, oy=118, s=20):
    p = SEASONS[st["season"]]
    night = st["phase"] == "night"
    rnd = random.Random(4)
    iso = Iso(ox, oy, s)
    lights, under, front, overlay_skip = [], [], [], []
    U = set(st["unlocked"])

    N = 9
    cells = [(x, y) for x in range(N) for y in range(N) if (x - 4) ** 2 + (y - 4) ** 2 <= 4.7 ** 2]
    for x, y in cells:
        iso.add(x, y, 0, p["top2"] if rnd.random() < .18 else p["top"], p["side"][0], p["side"][1])
        r2 = (x - 4) ** 2 + (y - 4) ** 2
        iso.add(x, y, -1, p["side"][0], p["side"][0], p["side"][1])
        for z, rr in [(-2, 3.7), (-3, 2.8), (-4, 1.9), (-5, 1.0)]:
            if r2 <= rr ** 2:
                iso.add(x, y, z, shade(p["side"][0], .95), shade(p["side"][0], .8), shade(p["side"][1], .75))
    used = set()

    def stone(x, y, z):
        iso.add(x, y, z, *STONE)
        used.add((x, y))

    def wood(x, y, z):
        iso.add(x, y, z, "#d9a877", "#b98a5e", "#9c7049")
        used.add((x, y))

    def roof(x, y, z):
        iso.add(x, y, z, p["roof"])

    def window(x, y, z, f, lit=True, shelf=False):
        col = "#ffd98a" if (night or lit) else "#3a3550"
        iso.put((x, y, z), f'<path d="{iso.face(x, y, z, f, .3, .2, .7, .72)}" fill="{col}"/>')
        if shelf:  # tiny manga spines in the hut window
            for k, c in enumerate(["#e98d8d", "#8fb8de", "#f2d27a", "#b9a6e0"]):
                iso.put((x, y, z), f'<path d="{iso.face(x, y, z, f, .33 + k * .09, .22, .4 + k * .09, .5)}" fill="{c}"/>')
        if night:
            cx, cy = iso.P(x + (1 if f == "px" else .5), y + (1 if f == "py" else .5), z + .5)
            lights.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="16" fill="url(#warm)" class="glow"/>')

    # --- tower (height grows with commits)
    tower_h = 2 + min(4, st["stats"]["commits"] // 600)
    for z in range(1, tower_h + 1):
        for x, y in [(2, 2), (3, 2), (2, 3), (3, 3)]:
            stone(x, y, z)
    iso.put((3, 3, 1), f'<path d="{iso.face(3, 3, 1, "py", .25, 0, .75, .8)}" fill="#6b4a36"/>')
    for z in range(3, tower_h + 1, 2):
        window(3, 2, z, "px", lit=False)
        window(2, 3, z, "py", lit=False)
    stairs = [(4, 4, 1), (4, 3, 2), (4, 2, 3), (4, 1, 4), (3, 1, 5), (2, 1, 6)][:max(2, tower_h - 1)]
    for x, y, z in stairs:
        stone(x, y, z)
    top_z = tower_h + 1
    gx, gy = iso.P(3, 3, top_z)
    iso.put((3, 3, tower_h), f'<circle cx="{gx:.0f}" cy="{gy:.0f}" r="50" fill="url(#halo)" class="glow"/>' + iso.flat_clover(3, 3, top_z, 1.0, p["leaf"]))
    if "castle" in U:  # turrets on the tower corners
        for x, y in [(2, 2), (3, 2), (2, 3)]:
            roof(x, y, top_z)
    if "observatory" in U:
        for z in (1, 2):
            stone(5, 1, z)
        dx, dy = iso.P(5.5, 1.5, 3)
        iso.put((5, 1, 2), f'<path d="M{dx - 18:.1f} {dy:.1f} a18 18 0 0 1 36 0z" fill="#e8edf5" stroke="#9aa4b8" stroke-width="1.4"/>'
                           f'<path d="M{dx - 3:.1f} {dy - 17:.1f} l14 -14 l4 4 l-14 14z" fill="#5a6078"/>')

    # --- hut (+ manga in the window), second hut
    def hut(x0, y0, sign=False):
        for x, y in [(x0, y0), (x0 + 1, y0), (x0, y0 + 1), (x0 + 1, y0 + 1)]:
            for z in (1, 2):
                wood(x, y, z)
            roof(x, y, 3)
        roof(x0, y0, 4)
        roof(x0 + 1, y0, 4)
        iso.put((x0 + 1, y0 + 1, 1), f'<path d="{iso.face(x0 + 1, y0 + 1, 1, "py", .3, 0, .7, .85)}" fill="#6b4a36"/>')
        window(x0 + 1, y0, 2, "px", lit=True, shelf=True)
        window(x0, y0 + 1, 2, "py", lit=True)
        if st["season"] == "winter":
            for x, y in [(x0, y0), (x0 + 1, y0)]:
                iso.put((x, y, 4), f'<path d="{iso.face(x, y, 4, "px", 0, .8, 1, 1)}" fill="#ffffff"/>')

    hut(6, 2)
    if "second hut" in U:
        hut(6, 5)

    # --- windmill
    if "windmill" in U:
        for z in (1, 2, 3):
            iso.add(1, 2, z, "#efe6da", "#d8c9b8", "#bfae9b")
            used.add((1, 2))
        roof(1, 2, 4)
        hx, hy = iso.P(2, 2.5, 3.6)
        blades = "".join(f'<path d="M0 0 L-3 -28 L3 -28Z" fill="#f3ece4" stroke="{shade(INK, 1.4)}" stroke-width="1" transform="rotate({a})"/>' for a in (0, 90, 180, 270))
        iso.put((1, 2, 4), f'<g transform="translate({hx:.1f} {hy:.1f})"><g class="spin">{blades}<circle r="3" fill="{INK}"/></g></g>')

    # --- reserved spot for holiday props (front, visible)
    hx, hy = 3, 7
    used.add((hx, hy))
    # --- you: sitting on the edge with a laptop, legs over the side
    used.update({(1, 7), (2, 7)})
    iso.put((1, 7, 0), coder(iso, 1, 7, night))
    if st["holiday"] == "new year":
        for c in [(2, 7), (4, 7), (3, 6), (3, 8)]:
            used.add(c)

    # --- districts by language share
    lang = st["langs"]
    tot = sum(l[1] for l in lang) or 1
    free = [(x, y) for x, y in cells if (x, y) not in used and 1 <= (x - 4) ** 2 + (y - 4) ** 2]
    angle = lambda c: (math.degrees(math.atan2(c[1] - 4, c[0] - 4)) - 45 + 360 + 180 / 2 * (lang[1][1] / tot if len(lang) > 1 else 0)) % 360
    order = [1, 0, 2, 3]  # python (the lake) faces the front, then TS, C++, other going round
    bounds, acc = [], 0
    for i in order:
        if i < len(lang):
            bounds.append((acc, acc + 360 * lang[i][1] / tot, i))
            acc += 360 * lang[i][1] / tot
    district = {}
    for c in free:
        a = angle(c)
        for lo, hi, i in bounds:
            if lo <= a < hi:
                district[c] = i
    # python lake (+ waterfall over the front edge)
    lake = sorted([c for c, i in district.items() if i == 1], key=lambda c: -(c[0] + c[1]))
    lake_n = max(2, round(len([c for c in district.values() if c == 1]) * .4))
    lake = lake[:lake_n]
    for x, y in lake:
        iso.cubes.pop((x, y, 0), None)
        iso.add(x, y, -1, p["water"], shade(p["water"], .85), shade(p["water"], .7))
        used.add((x, y))
    waterfall = None
    if "waterfall" in U and lake:
        edge = max(lake, key=lambda c: c[1] * 10 + c[0])
        waterfall = edge
    for c, i in district.items():
        if c in used:
            continue
        x, y = c
        if i == 0 and rnd.random() < .32:  # typescript forest
            h = rnd.choice([1, 1, 2])
            for z in range(1, h + 1):
                iso.add(x, y, z, shade(p["side"][1], 1.05), shade(p["side"][1], .9), shade(p["side"][1], .8))
            iso.add(x, y, h + 1, p["crown"])
            used.add(c)
        elif i == 2 and rnd.random() < .35:  # c++ cliffs
            for z in range(1, rnd.choice([1, 2]) + 1):
                iso.add(x, y, z, "#c9c3cf", "#a9a2b3", "#8e879a")
            used.add(c)
        else:  # meadow: flowers and tufts
            fx, fy = iso.P(x + rnd.uniform(.3, .7), y + rnd.uniform(.3, .7), 1)
            if rnd.random() < .5:
                iso.put((x, y, 0), f'<path d="M{fx:.1f} {fy:.1f} v-7" stroke="#4f8a5b" stroke-width="1.4"/>'
                        + "".join(f'<circle cx="{fx + dx:.1f}" cy="{fy - 8 + dy:.1f}" r="2.2" fill="{p["flower"]}"/>' for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)))
                        + f'<circle cx="{fx:.1f}" cy="{fy - 8:.1f}" r="1.3" fill="#ffe7a3"/>')
            else:
                iso.put((x, y, 0), "".join(f'<path d="M{fx + dx:.1f} {fy:.1f} q{dx * .4:.1f} -5 {dx * .9:.1f} -9" stroke="{shade(p["leaf"], .8)}" '
                                           f'stroke-width="1.5" fill="none" stroke-linecap="round"/>' for dx in (-3, 0, 3)))

    # --- holiday props
    if st["holiday"] == "halloween":
        iso.add(hx, hy, 1, "#f08a3c", "#d9742a", "#bf6020")
        iso.put((hx, hy, 1), f'<path d="{iso.face(hx, hy, 1, "py", .2, .45, .4, .7)}" fill="#2b2540"/><path d="{iso.face(hx, hy, 1, "py", .6, .45, .8, .7)}" fill="#2b2540"/>'
                             f'<path d="{iso.face(hx, hy, 1, "py", .25, .15, .75, .3)}" fill="#2b2540"/>')
        if night:
            cx, cy = iso.P(hx + .5, hy + 1, 1.5)
            lights.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="20" fill="url(#warm)" class="glow"/>')
    elif st["holiday"] == "new year":
        # voxel fir: two wide tiers, a narrow top, a gold star cube; garland lights on the visible faces
        g1, g2, g3 = "#4f9a62", "#5fae72", "#6fbf80"
        plus = [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)]
        iso.add(hx, hy, 1, "#8f6643")  # trunk
        for dx, dy in plus:
            iso.add(hx + dx, hy + dy, 2, g1)
        iso.add(hx, hy, 3, g2)
        iso.add(hx, hy, 4, g3)
        iso.add(hx, hy, 5, "#f2c94c", "#d9ad35", "#c0962a")
        if st["season"] == "winter":  # snow on the lower tier
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                iso.put((hx + dx, hy + dy, 2), f'<path d="{iso.face(hx + dx, hy + dy, 2, "top", .1, .1, .9, .9)}" fill="#ffffff" opacity=".85"/>')
        bulbs = ["#ffd98a", "#f28b82", "#9fd0ec", "#f5a9bf"]
        for (x, y, z, f) in [(hx + 1, hy, 2, "px"), (hx, hy + 1, 2, "py"), (hx, hy, 3, "px"), (hx, hy, 3, "py"), (hx, hy, 4, "px"), (hx, hy, 4, "py")]:
            for k in range(3):
                u, v = rnd.uniform(.15, .85), rnd.uniform(.2, .8)
                cx, cy = iso.P(x + (1 if f == "px" else u), y + (1 if f == "py" else u), z + v)
                lights.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="2.6" fill="{rnd.choice(bulbs)}" class="tw" style="animation-delay:{-rnd.uniform(0, 2):.1f}s"/>')
        sx_, sy_ = iso.P(hx + .5, hy + .5, 6.3)
        lights.append(sparkle(sx_, sy_, 9, fill="#ffe7a3"))
        if night:
            cx, cy = iso.P(hx + .5, hy + .5, 3)
            lights.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="44" fill="url(#warm)" class="glow"/>')
        # gift boxes
        for (x, y), c in [((2, 8), "#e98d8d"), ((4, 8), "#8fb8de")]:
            if (x, y, 0) in iso.cubes:
                gb = Iso(*iso.P(x + .5, y + .2, 1), 6)
                gb.add(0, 0, 0, c)
                gb.put((0, 0, 0), f'<path d="{gb.face(0, 0, 0, "top", .42, 0, .58, 1)}" fill="#fff7d6"/><path d="{gb.face(0, 0, 0, "top", 0, .42, 1, .58)}" fill="#fff7d6"/>')
                front.append(gb.render())
    elif st["holiday"] == "nooruz":
        a0, a1 = iso.P(3, 2.5, tower_h + .6), iso.P(7, 2.5, 4.6)
        flags = ""
        for k in range(1, 8):
            t = k / 8
            fx = a0[0] + (a1[0] - a0[0]) * t
            fy = a0[1] + (a1[1] - a0[1]) * t + 16 * math.sin(math.pi * t)
            flags += f'<path d="M{fx - 5:.1f} {fy:.1f} L{fx + 5:.1f} {fy:.1f} L{fx:.1f} {fy + 10:.1f}Z" fill="{["#e63946", "#f4a261", "#2a9d8f", "#e9c46a"][k % 4]}"/>'
        front.append(f'<path d="M{a0[0]:.1f} {a0[1]:.1f} Q{(a0[0] + a1[0]) / 2:.1f} {(a0[1] + a1[1]) / 2 + 18:.1f} {a1[0]:.1f} {a1[1]:.1f}" stroke="{INK}" stroke-width="1.2" fill="none"/>{flags}')

    body = iso.render()

    # waterfall
    if waterfall:
        x, y = waterfall
        a0, a1 = iso.P(x, y + 1, 0), iso.P(x + 1, y + 1, 0)
        depth = 100  # the water thins out into mist instead of running off the card
        wf = (f'<linearGradient id="wfade" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{p["water"]}" stop-opacity=".9"/>'
              f'<stop offset=".6" stop-color="{p["water"]}" stop-opacity=".55"/><stop offset="1" stop-color="{p["water"]}" stop-opacity="0"/></linearGradient>'
              f'<path d="M{a0[0]:.1f} {a0[1]:.1f} L{a1[0]:.1f} {a1[1]:.1f} L{a1[0]:.1f} {a1[1] + depth:.1f} L{a0[0]:.1f} {a0[1] + depth:.1f}Z" fill="url(#wfade)"/>')
        for k in range(5):
            xk = a0[0] + (a1[0] - a0[0]) * (k + .5) / 5
            yk = a0[1] + (a1[1] - a0[1]) * (k + .5) / 5
            wf += f'<path d="M{xk:.1f} {yk:.1f} V{yk + depth * .8:.1f}" stroke="#ffffff" stroke-width="1.6" stroke-dasharray="10 18" class="pour" style="animation-delay:{-k * .27:.2f}s" opacity=".6"/>'
        mx, my = (a0[0] + a1[0]) / 2, a1[1] + depth * .85
        wf += "".join(f'<circle cx="{mx + dx:.1f}" cy="{my + dy:.1f}" r="{r}" fill="#ffffff" opacity=".28" class="glow" style="animation-delay:{-k:.1f}s"/>'
                      for k, (dx, dy, r) in enumerate([(-10, 0, 10), (8, 4, 12), (0, 12, 9), (-16, 12, 7), (16, 14, 7)]))
        front.append(wf)
        if "rainbow" in st["rare"]:
            cx, cy = (a0[0] + a1[0]) / 2, a1[1] + 90
            front.insert(0, "".join(f'<path d="M{cx - r} {cy} A{r} {r} 0 0 1 {cx + r} {cy}" stroke="{c}" stroke-width="5" fill="none" opacity=".45"/>'
                                    for r, c in zip(range(150, 115, -7), ["#f28b82", "#fbbc6c", "#fde58a", "#9fd6a8", "#8fb8de", "#b9a6e0"])))
    # vines + crystals under the island
    for k in range(9):
        vx, vy = iso.P(rnd.uniform(1.5, 8), rnd.uniform(1.5, 8), -2)
        ln = rnd.uniform(20, 46)
        under.append(f'<path d="M{vx:.1f} {vy:.1f} q{rnd.uniform(-6, 6):.1f} {ln / 2:.1f} 0 {ln:.1f}" stroke="{shade(p["leaf"], .75)}" stroke-width="1.8" '
                     f'fill="none" stroke-linecap="round" class="vine" style="animation-delay:{-rnd.uniform(0, 4):.1f}s"/>')
    cx_, cy_ = iso.P(4.5, 4.5, -5)
    for dx, h, col in [(-10, 22, "#b9a6e0"), (4, 30, "#cdb8f0"), (14, 16, "#a58fd6")]:
        under.append(f'<path d="M{cx_ + dx - 5:.1f} {cy_:.1f} L{cx_ + dx:.1f} {cy_ + h:.1f} L{cx_ + dx + 5:.1f} {cy_:.1f}Z" fill="{col}"/>')
        if night:
            lights.append(f'<circle cx="{cx_ + dx:.1f}" cy="{cy_ + h / 2:.1f}" r="12" fill="#cdb8f0" opacity=".35" class="glow"/>')

    # islet: bridge, garden of found clovers, bench (+cat), lantern / lighthouse, clay modules
    islet_markup = ""
    if "islet" in U:
        il = Iso(ox, oy, s)
        for x in (11, 12):
            for y in (3, 4, 5):
                il.add(x, y, 0, p["top"], p["side"][0], p["side"][1])
        for x, y in [(11, 4), (12, 4)]:
            il.add(x, y, -1, shade(p["side"][0], .95), shade(p["side"][0], .8), shade(p["side"][1], .75))
        # lighthouse or lantern
        if "lighthouse" in U:
            for z in (1, 2, 3):
                il.add(12, 3, z, "#f3ece4" if z % 2 else "#e98d8d")
            lx, ly = il.P(12.5, 3.5, 4)
            il.put((12, 3, 3), f'<rect x="{lx - 6:.1f}" y="{ly - 14:.1f}" width="12" height="14" fill="#ffd98a" stroke="{INK}" stroke-width="1.4"/>'
                               f'<path d="M{lx - 8:.1f} {ly - 14:.1f} L{lx:.1f} {ly - 24:.1f} L{lx + 8:.1f} {ly - 14:.1f}Z" fill="{p["roof"]}"/>')
            if night or st["phase"] == "evening":
                lights.append(f'<path d="M{lx:.1f} {ly - 7:.1f} L{lx + 170:.1f} {ly - 50:.1f} L{lx + 170:.1f} {ly + 30:.1f}Z" fill="#ffe7a3" class="beam"/>')
        else:
            lx, ly = il.P(12.5, 3.5, 1)
            il.put((12, 3, 0), f'<path d="M{lx:.1f} {ly:.1f} V{ly - 34:.1f}" stroke="#3a3550" stroke-width="2.5"/>'
                               f'<rect x="{lx - 5:.1f}" y="{ly - 46:.1f}" width="10" height="12" rx="2" fill="#ffd98a" stroke="#3a3550" stroke-width="1.5"/>')
            lights.append(f'<circle cx="{lx:.1f}" cy="{ly - 40:.1f}" r="{20 if night else 12}" fill="url(#warm)" class="glow"/>')
        # bench (+ cat sometimes)
        bx0, by0 = il.P(11.2, 5.4, 1)
        bench = (f'<path d="M{bx0:.1f} {by0:.1f} l18 9 M{bx0:.1f} {by0 - 7:.1f} l18 9" stroke="#8f6643" stroke-width="3" stroke-linecap="round"/>'
                 f'<path d="M{bx0 + 2:.1f} {by0 + 1:.1f} v6 M{bx0 + 16:.1f} {by0 + 8:.1f} v6" stroke="#6b4a36" stroke-width="2"/>')
        if "cat" in st["rare"]:
            cxk, cyk = bx0 + 9, by0 - 4
            bench += (f'<ellipse cx="{cxk:.1f}" cy="{cyk:.1f}" rx="6" ry="4.5" fill="#2b2540"/><circle cx="{cxk + 5:.1f}" cy="{cyk - 5:.1f}" r="3.6" fill="#2b2540"/>'
                      f'<path d="M{cxk + 3:.1f} {cyk - 8:.1f} l1 -3 l1.5 3 M{cxk + 6:.1f} {cyk - 8:.1f} l1 -3 l1.5 3" fill="#2b2540"/>'
                      f'<path d="M{cxk - 6:.1f} {cyk:.1f} q-6 -2 -5 -9" stroke="#2b2540" stroke-width="2" fill="none" stroke-linecap="round"/>')
        il.put((11, 5, 0), bench)
        # garden: one standing clover per lucky day, the newest one glows if today is lucky
        n = min(st["found"], 12)
        spots = [(11.25 + (k % 4) * .5, 3.2 + (k // 4) * .45) for k in range(n)]
        garden = ""
        for k, (gxk, gyk) in enumerate(spots):
            px_, py_ = il.P(gxk, gyk, 1)
            newest = st["lucky"] and k == n - 1
            if newest:
                garden += f'<circle cx="{px_:.1f}" cy="{py_ - 14:.1f}" r="26" fill="url(#halo)" class="glow"/>'
            garden += f'<g class="sway2">{standing_clover(px_, py_, 5.5 if not newest else 7, p["leaf"], 4, 14 if not newest else 20)}</g>'
        il.put((11, 3, 0), garden)
        # clay modules (tiny cubes) by the bench
        clay = Iso(*il.P(12.2, 5.1, 1), 5)
        for (x, y, z), c in [((0, 0, 0), "#e9b3a0"), ((1, 0, 0), "#a9c9e9"), ((0, 0, 1), "#f2d27a")]:
            clay.add(x, y, z, c)
        il.put((12, 5, 0), clay.render())
        bridge = ""
        for k in range(9):
            bridge += f'<path d="{iso.face(9 + k * .22, 4, 0, "top", 0, 0, .17, 1)}" fill="#c99a6a" stroke="#8f6643" stroke-width=".8"/>'
        r0, r1 = iso.P(9, 4, 1.3), iso.P(11, 4, 1.3)
        bridge += f'<path d="M{r0[0]:.1f} {r0[1]:.1f} Q{(r0[0] + r1[0]) / 2:.1f} {(r0[1] + r1[1]) / 2 + 8:.1f} {r1[0]:.1f} {r1[1]:.1f}" stroke="#8f6643" stroke-width="1.6" fill="none"/>'
        islet_markup = bridge + il.render()

    # now-building signpost by the hut
    if st["repo"]:
        sx0, sy0 = iso.P(5.5, 3.5, 1)
        front.append(f'<path d="M{sx0:.1f} {sy0:.1f} v-26" stroke="#6b4a36" stroke-width="3"/>'
                     f'<path d="M{sx0 - 2:.1f} {sy0 - 30:.1f} l26 13 v10 l-26 -13z" fill="#e7c49a" stroke="#6b4a36" stroke-width="1.6"/>')

    # second islet: a little floating rock with a tree, drifting on its own
    if "second islet" in U:
        i2 = Iso(ox - 250, oy + 210, s * .8)
        for x, y in [(0, 0), (1, 0), (0, 1), (1, 1)]:
            i2.add(x, y, 0, p["top"], p["side"][0], p["side"][1])
        i2.add(0, 0, -1, shade(p["side"][0], .9))
        i2.add(1, 1, 1, shade(p["side"][1], 1.05)); i2.add(1, 1, 2, p["crown"])
        front.append(f'</g><g class="bob2">{i2.render()}</g><g>')

    # balloon, built from cubes like everything else
    extra_air = ""
    if "balloon" in U:
        bx_, by_ = ox - 230, oy + 40
        bal = Iso(bx_, by_, 8)
        stripes = ["#e98d8d", "#f6e1c8"]
        layers = {0: [(1, 1), (2, 1), (1, 2), (2, 2)],
                  1: [(x, y) for x in range(4) for y in range(4) if (x, y) not in [(0, 0), (3, 3), (0, 3), (3, 0)]],
                  2: [(x, y) for x in range(4) for y in range(4)],
                  3: [(x, y) for x in range(4) for y in range(4)],
                  4: [(x, y) for x in range(4) for y in range(4) if (x, y) not in [(0, 0), (3, 3), (0, 3), (3, 0)]],
                  5: [(1, 1), (2, 1), (1, 2), (2, 2)]}
        for z, cs in layers.items():
            for x, y in cs:
                bal.add(x, y, z + 4, stripes[x % 2])
        bal.add(1, 1, 0, "#c99a6a", "#a97a4c", "#8f6643")  # basket
        bal.add(2, 1, 0, "#c99a6a", "#a97a4c", "#8f6643")
        bal.add(1, 2, 0, "#c99a6a", "#a97a4c", "#8f6643")
        bal.add(2, 2, 0, "#c99a6a", "#a97a4c", "#8f6643")
        ropes = ""
        for (x, y) in [(1, 1), (3, 1), (1, 3), (3, 3)]:
            p0, p1 = bal.P(x, y, 1), bal.P(x + (0 if x == 1 else 0), y, 4)
            ropes += f'<path d="M{p0[0]:.1f} {p0[1]:.1f} L{p1[0]:.1f} {p1[1]:.1f}" stroke="{INK}" stroke-width="1" opacity=".55"/>'
        extra_air = f'<g class="fly">{ropes}{bal.render()}</g>'
    # fireflies on summer nights
    if night and st["season"] in ("summer", "spring"):
        for k in range(10):
            fx, fy = iso.P(rnd.uniform(0, 9), rnd.uniform(0, 9), rnd.uniform(1, 3))
            lights.append(f'<circle cx="{fx:.0f}" cy="{fy:.0f}" r="2" fill="#f7f3a0" class="tw" style="animation-delay:{-rnd.uniform(0, 2):.1f}s"/>')

    world = f'<g class="bob">{"".join(under)}{body}{islet_markup}{"".join(front)}</g>{extra_air}'
    return world, "".join(lights), iso


# ---------------------------------------------------------------- the dog
DOG_NAME = "keko"


def dog_mood(st):
    """happy: committed today · waiting: not yet today · sleep: night, or 3+ quiet days."""
    days = (st.get("calendar") or {}).get("days") or []
    if st["phase"] == "night":
        return "sleep"
    if not days:
        return "waiting"
    if days[-1][1] > 0:
        return "happy"
    quiet = 0
    for _, c in reversed(days):
        if c:
            break
        quiet += 1
    return "sleep" if quiet >= 3 else "waiting"


def ibox(P, x, y, z, dx, dy, dz, top, py, px):
    return (f'<path d="{poly([P(x, y, z + dz), P(x + dx, y, z + dz), P(x + dx, y + dy, z + dz), P(x, y + dy, z + dz)])}" fill="{top}"/>'
            f'<path d="{poly([P(x, y + dy, z), P(x + dx, y + dy, z), P(x + dx, y + dy, z + dz), P(x, y + dy, z + dz)])}" fill="{py}"/>'
            f'<path d="{poly([P(x + dx, y, z), P(x + dx, y + dy, z), P(x + dx, y + dy, z + dz), P(x + dx, y, z + dz)])}" fill="{px}"/>')


def _C(c, d=1):
    return shade(c, 1.07 * d), shade(c, .86 * d), shade(c, .7 * d)


def dog(P, v, mood, night):
    """A voxel leonberger (golden coat, lighter mane, black mask, dark hanging ears), facing the viewer (+y).
    P: projection in voxel units, v: pixels per voxel (for strokes)."""
    d = .8 if night else 1
    coat, leg, mane, ear, mask, paw = "#cf8f4c", "#b0723c", "#e6b071", "#5a3620", "#2a2230", "#e9c08e"
    B = lambda x, y, z, dx, dy, dz, c: out.append(ibox(P, x, y, z, dx, dy, dz, *_C(c, d)))  # noqa: E731
    out = []
    face = lambda y, x0, z0, x1, z1: poly([P(x0, y, z0), P(x1, y, z0), P(x1, y, z1), P(x0, y, z1)])  # noqa: E731

    if mood == "happy":   # standing, tail wagging, tongue out
        ax, ay = P(3, 1, 7.6)
        tail = []
        for (x, y, z, dx, dy, dz) in [(2.2, -1.2, 7.4, 1.6, 1.6, 1.6), (2.2, -2.4, 8.6, 1.6, 1.6, 1.8), (2.3, -2.9, 10.2, 1.4, 1.4, 1.4)]:
            tail.append(ibox(P, x, y, z, dx, dy, dz, *_C(mane, d)))
        out.append(f'<g class="wag" style="transform-origin:{ax:.1f}px {ay:.1f}px">{"".join(tail)}</g>')
        for x in (1, 3.6):
            B(x, 1.2, 0, 1.4, 1.6, 4.2, leg); B(x, 1.2, 0, 1.4, 1.6, 1, paw)
        B(.6, 1, 4, 4.8, 8.6, 4, coat)
        B(1.6, 1.4, 8, 2.8, 6, .5, shade(coat, .9))          # darker saddle
        for x in (1, 3.6):
            B(x, 8.2, 0, 1.4, 1.6, 4.2, leg); B(x, 8.2, 0, 1.4, 1.6, 1, paw)
        B(0, 7.4, 3.6, 6, 3.4, 5.6, mane)                     # the lion mane
        B(.9, 9.2, 8.6, 4.2, 1.4, .7, "#d9534f")              # collar
        tgx, tgy = P(3, 10.6, 8.4)
        out.append(f'<circle cx="{tgx:.1f}" cy="{tgy:.1f}" r="{v * .45:.1f}" fill="#ffd25a" stroke="#b8862e" stroke-width="1"/>')
        B(.4, 10.2, 9, 1.1, 2.2, 3.2, ear)
        B(1, 9.6, 8.4, 4, 3.6, 4, coat)                        # head
        B(.2, 12.6, 8.2, 5.6, .3, 1.2, mane)                   # cheek fluff
        B(1.9, 13.2, 8.4, 2.2, 2, 2, mask)                     # muzzle
        out.append(f'<path d="{face(13.21, 1.1, 10.2, 4.9, 11.6)}" fill="{shade(mask, 1.4)}" opacity=".55"/>')   # mask round the eyes
        out.append('<g class="blink">' + "".join(f'<path d="{face(13.22, ex, 10.6, ex + .9, 11.3)}" fill="#f7f1e3"/><path d="{face(13.23, ex + .2, 10.6, ex + .7, 11.1)}" fill="{INK}"/>' for ex in (1.5, 3.6)) + '</g>')
        out.append(f'<path d="{face(15.21, 2.6, 9.2, 3.4, 10.4)}" fill="{INK}"/>')                # nose
        out.append(f'<path d="{face(15.22, 2.6, 7.4, 3.4, 8.6)}" fill="#f08a9a"/>')               # tongue
        B(4.5, 10.2, 9, 1.1, 2.2, 3.2, ear)
    else:                 # lying: head up while waiting, head on the paws while asleep
        sleep = mood == "sleep"
        tail = [(5.6, 1.5, 0, 1.4, 3, 1.4), (5.4, 4.5, 0, 1.4, 3, 1.2)] if sleep else [(2.2, -1.6, 0, 1.6, 2.8, 1.4), (2.3, -3.6, .2, 1.4, 2.2, 1.2)]
        for t in tail[::-1] if not sleep else []:
            B(*t, mane)
        B(.4, 1, 0, 5.2, 8.6, 3.8, coat)
        B(1.4, 1.4, 3.8, 3.2, 6, .4, shade(coat, .9))
        if sleep:
            for t in tail:
                B(*t, mane)
        B(0, 7.4, 0, 6, 3.4, 5, mane)
        if not sleep:
            B(.9, 9.2, 4.9, 4.2, 1.4, .7, "#d9534f")
        for x in (1, 3.6):
            B(x, 10.4, 0, 1.4, 3.8, 1, paw)
        hz = 1 if sleep else 4.6
        B(.4, 10.2, hz + .8, 1.1, 2.2, 3, ear)
        B(1, 9.6, hz, 4, 3.6, 4, coat)
        B(1.9, 13.2, hz, 2.2, 2, 2, mask)
        out.append(f'<path d="{face(13.21, 1.1, hz + 1.8, 4.9, hz + 3.2)}" fill="{shade(mask, 1.4)}" opacity=".55"/>')
        out.append(f'<path d="{face(15.21, 2.6, hz + .8, 3.4, hz + 2)}" fill="{INK}"/>')
        if sleep:
            for ex in (1.5, 3.6):
                out.append(f'<path d="{face(13.22, ex, hz + 2.2, ex + .9, hz + 2.5)}" fill="{INK}"/>')
        else:
            out.append('<g class="blink">' + "".join(f'<path d="{face(13.22, ex, hz + 2.2, ex + .9, hz + 2.9)}" fill="#f7f1e3"/><path d="{face(13.23, ex + .2, hz + 2.2, ex + .7, hz + 2.7)}" fill="{INK}"/>' for ex in (1.5, 3.6)) + '</g>')
        B(4.5, 10.2, hz + .8, 1.1, 2.2, 3, ear)
        if sleep:
            zx, zy = P(5, 12, hz + 6)
            for k in range(3):
                out.append(f'<path d="M{zx:.1f} {zy:.1f} h{v * 1.4:.1f} l{-v * 1.4:.1f} {v * 1.6:.1f} h{v * 1.4:.1f}" stroke="{"#e8e4f4" if night else INK}" '
                           f'stroke-width="{v * .35:.1f}" fill="none" stroke-linejoin="round" class="zz" style="animation-delay:{k:.0f}s"/>')
    title = {"happy": "happy: there was a commit today", "waiting": "waiting for today's commit", "sleep": "asleep"}[mood]
    return f'<g><title>{DOG_NAME} is {title}</title>{"".join(out)}</g>'


def dog_friends(P, v, mood, night, opened, cx0, cy0):
    """So keko is not bored: a ball, a little bird on the chest, a butterfly (a firefly at night)."""
    out = []
    # ball: bounces when keko is happy, otherwise rests by the paws
    bx, by = P(8.2, 14.5, 0)
    ball = (f'<circle cx="{bx:.1f}" cy="{by - 9:.1f}" r="9" fill="#e0574c"/>'
            f'<path d="M{bx - 9:.1f} {by - 9:.1f} a9 9 0 0 0 18 0z" fill="#f7f1e3"/>'
            f'<path d="M{bx - 9:.1f} {by - 9:.1f} h18" stroke="{INK}" stroke-width="1.4"/><circle cx="{bx - 3:.1f}" cy="{by - 13:.1f}" r="2" fill="#ffffff" opacity=".7"/>')
    out.append(f'<ellipse cx="{bx:.1f}" cy="{by:.1f}" rx="8" ry="3" fill="{INK}" opacity=".15"/>')
    out.append(f'<g class="bounce">{ball}</g>' if mood == "happy" else ball)
    # a little bird on the chest (not at night)
    if not night:
        wx, wy = P(cx0 + 8.6, cy0 - .7, 13.2) if opened else P(cx0 + 7.5, cy0 + 3, 8.6)
        bird = (f'<ellipse cx="{wx:.1f}" cy="{wy - 6:.1f}" rx="7" ry="5.5" fill="#6a8fd6"/>'
                f'<circle cx="{wx - 5:.1f}" cy="{wy - 11:.1f}" r="4.2" fill="#6a8fd6"/>'
                f'<path d="M{wx - 9:.1f} {wy - 11:.1f} l-4 1.5 l4 1.5z" fill="#f0a63c"/>'
                f'<circle cx="{wx - 6:.1f}" cy="{wy - 12:.1f}" r="1.1" fill="{INK}"/>'
                f'<ellipse cx="{wx - 1:.1f}" cy="{wy - 4:.1f}" rx="4" ry="2.6" fill="#f3eee6"/>'
                f'<path d="M{wx + 6:.1f} {wy - 7:.1f} l6 -3 l-1 5z" fill="#4f6fb4"/>'
                f'<path d="M{wx - 2:.1f} {wy - 1:.1f} v2 M{wx + 1:.1f} {wy - 1:.1f} v2" stroke="#f0a63c" stroke-width="1.2"/>')
        out.append(f'<g class="hop">{bird}</g>')
    # butterfly (firefly at night) circling around keko's head
    hx, hy = P(3, 12, 14.5)
    path = f"M{hx + 34:.1f} {hy:.1f} a34 13 0 1 1 -68 0 a34 13 0 1 1 68 0"
    if night:
        bug = '<circle r="6" fill="url(#halo)" opacity=".9"/><circle r="2" fill="#f7f3a0"/>'
    else:
        bug = ('<g class="flap"><path d="M0 0 C-7 -9 -10 -2 -2 1Z M0 0 C7 -9 10 -2 2 1Z" fill="#f5a9bf"/>'
               '<path d="M0 0 C-5 6 -7 2 -1 1Z M0 0 C5 6 7 2 1 1Z" fill="#e98d8d"/></g><path d="M0 -3 v5" stroke="#2b2540" stroke-width="1.2"/>')
    out.append(f'<g>{bug}<animateMotion dur="9s" repeatCount="indefinite" path="{path}"/></g>')
    return "".join(out)


SYNODIC = 29.530588853
PHASE_NAMES = ["new moon", "waxing crescent", "first quarter", "waxing gibbous",
               "full moon", "waning gibbous", "last quarter", "waning crescent"]


def moon_age(day):
    """Days since the last new moon, at midnight in Bishkek (18:00 UTC). Reference new moon: 2000-01-06 18:14 UTC."""
    from datetime import datetime, timezone
    ref = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
    t = datetime(day.year, day.month, day.day, 18, 0, tzinfo=timezone.utc)
    return ((t - ref).total_seconds() / 86400) % SYNODIC


def moon_name(day):
    return PHASE_NAMES[int((moon_age(day) / SYNODIC) * 8 + .5) % 8]


def moon(day, cx, cy, R):
    """Tonight's real moon: lit part = outer half-circle + elliptic terminator (northern hemisphere view)."""
    age = moon_age(day)
    th = 2 * math.pi * age / SYNODIC
    lit = (1 - math.cos(th)) / 2
    rx = R * abs(math.cos(th))
    top, bot = f"{cx:.1f} {cy - R:.1f}", f"{cx:.1f} {cy + R:.1f}"
    if th < math.pi:   # waxing: right side lit
        d = f"M{top} A{R} {R} 0 0 1 {bot} A{rx:.2f} {R} 0 0 {0 if math.cos(th) > 0 else 1} {top}Z"
    else:              # waning: left side lit
        d = f"M{top} A{R} {R} 0 0 0 {bot} A{rx:.2f} {R} 0 0 {1 if math.cos(th) > 0 else 0} {top}Z"
    out = [f'<g><title>{moon_name(day)} · {round(lit * 100)}% lit</title>',
           f'<circle cx="{cx}" cy="{cy}" r="{R * 3.2:.0f}" fill="url(#halo)" opacity="{.15 + .5 * lit:.2f}"/>',
           f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="#ffffff" opacity=".1"/>']
    if lit > .01:
        out.append(f'<clipPath id="moonlit"><path d="{d}"/></clipPath><path d="{d}" fill="#f4f1e6"/>'
                   f'<g clip-path="url(#moonlit)" fill="#d9d3c2">'
                   f'<circle cx="{cx - R * .3:.1f}" cy="{cy - R * .25:.1f}" r="{R * .2:.1f}"/>'
                   f'<circle cx="{cx + R * .35:.1f}" cy="{cy + R * .2:.1f}" r="{R * .14:.1f}"/>'
                   f'<circle cx="{cx - R * .05:.1f}" cy="{cy + R * .45:.1f}" r="{R * .1:.1f}"/></g>')
    out.append('</g>')
    return "".join(out)


def sky_layer(st, W, H, rnd):
    """Weather and sky decoration drawn behind/in front of the island."""
    back, fore = [], []
    p = SEASONS[st["season"]]
    night = st["phase"] == "night"
    if night:
        for _ in range(60):
            x, y = rnd.uniform(0, W), rnd.uniform(0, H * .55)
            back.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{rnd.choice([.8, 1, 1.3])}" fill="#fff" class="tw" style="animation-delay:{-rnd.uniform(0, 3):.1f}s;animation-duration:{rnd.uniform(2, 5):.1f}s"/>')
        back.append(moon(st["today"], W - 120, 78, 24))
        if "aurora" in st["rare"]:
            for k, c in enumerate(["#7ee0b5", "#9fd0ec", "#c9a6f0"]):
                back.append(f'<path d="M600 {70 + k * 18} C760 {20 + k * 20} 900 {120 + k * 10} 1200 {50 + k * 22}" stroke="{c}" stroke-width="{26 - k * 6}" fill="none" '
                            f'opacity=".35" class="aurora" style="animation-delay:{-k * 3}s" stroke-linecap="round"/>')
        if "shooting star" in st["rare"]:
            back.append(f'<path d="M520 30 L700 110" stroke="#fff" stroke-width="2" stroke-linecap="round" class="star"/>')
    elif st["weather"] in ("sunny", "clear"):
        sx = W - 120 if st["phase"] != "evening" else W - 160
        sy = 80 if st["phase"] == "day" else 130
        back.append(f'<circle cx="{sx}" cy="{sy}" r="72" fill="url(#halo)" class="glow"/><circle cx="{sx}" cy="{sy}" r="26" fill="#ffe3a0"/>')
    clouds = {"sunny": 1, "clear": 2, "cloudy": 5, "rain": 6}[st["weather"]]
    ccol = "#ffffff" if st["weather"] in ("sunny", "clear") else "#e6e8ef"
    if night:
        ccol = "#5a5c87"
    for k in range(clouds):
        cx, cy, sc = rnd.uniform(660, 1120), rnd.uniform(40, 220), rnd.uniform(.7, 1.2)
        back.append(f'<g class="drift" style="animation-delay:{-k * 6}s" opacity=".8"><ellipse cx="{cx:.0f}" cy="{cy:.0f}" rx="{70 * sc:.0f}" ry="{20 * sc:.0f}" fill="{ccol}"/>'
                    f'<ellipse cx="{cx + 30 * sc:.0f}" cy="{cy - 14 * sc:.0f}" rx="{40 * sc:.0f}" ry="{20 * sc:.0f}" fill="{ccol}"/></g>')
    # precipitation
    if st["weather"] == "rain":
        kind = "snow" if st["season"] == "winter" else "rain"
    else:
        kind = p["fall"]
        if st["season"] == "winter" and st["weather"] in ("sunny", "clear"):
            kind = None
    if kind == "rain":
        for _ in range(70):
            x, y = rnd.uniform(0, W + 40), rnd.uniform(-60, H)
            fore.append(f'<path d="M{x:.0f} {y:.0f} l-5 18" stroke="#8fa6c8" stroke-width="1.4" opacity=".6" class="rain" style="animation-delay:{-rnd.uniform(0, .7):.2f}s"/>')
    elif kind:
        n = {"snow": 60, "petals": 26, "leaves": 22}[kind]
        for _ in range(n):
            x, y = rnd.uniform(0, W), rnd.uniform(-80, H * .5)
            dur = rnd.uniform(9, 16)
            dx, dy, r = rnd.uniform(20, 90), H + 100, rnd.choice([-1, 1]) * rnd.uniform(120, 420)
            if kind == "snow":
                body = f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{rnd.uniform(1.8, 3.4):.1f}" fill="#fff"/>'
            elif kind == "petals":
                body = f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="5.5" ry="3.2" fill="#f5a9bf"/>'
            else:
                body = f'<rect x="{x:.0f}" y="{y:.0f}" width="7" height="7" rx="1.5" fill="{rnd.choice(["#e7a85d", "#d9874b", "#f0c06a"])}"/>'
            fore.append(f'<g class="fall" style="--dx:{dx:.0f}px;--dy:{dy:.0f}px;--r:{r:.0f}deg;transform-origin:{x:.0f}px {y:.0f}px;'
                        f'animation-duration:{dur:.1f}s;animation-delay:{-rnd.uniform(0, dur):.1f}s">{body}</g>')
    if not night:
        for k, (bx, by) in enumerate([(700, 70), (730, 58), (1080, 110)]):
            back.append(f'<path d="M{bx} {by} q5 -5 10 0 q5 -5 10 0" stroke="#4a4560" stroke-width="1.8" fill="none" stroke-linecap="round" class="bird" style="animation-delay:{-k * 1.7:.1f}s"/>')
    return "".join(back), "".join(fore)


PIXEL = {  # 5x7 block letters
    "B": ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
    "I": ["###", ".#.", ".#.", ".#.", ".#.", ".#.", "###"],
    "L": ["#....", "#....", "#....", "#....", "#....", "#....", "#####"],
    "M": ["#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"],
    "0": [".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."],
    "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    "3": ["####.", "....#", "....#", ".###.", "....#", "....#", "####."],
    "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    "5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
    "6": [".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."],
    "7": ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
    "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    "9": [".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."],
    ",": ["..", "..", "..", "..", "..", "#.", "#."],
    "H": ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    " ": ["..", "..", "..", "..", "..", "..", ".."],
}


def block_name(word, x0, y0, s, st, mode="oblique"):
    """The name built from cubes. oblique: letters stay horizontal (front faces square), depth goes up-right."""
    p = SEASONS[st["season"]]
    night = st["phase"] == "night"
    body = ("#efe6da", "#d6c9b8", "#bfae9b") if night else ("#4a4270", "#2b2540", "#3b3358")
    cells = []
    col = 0
    for ch in word:
        g = PIXEL[ch]
        for r, row in enumerate(g):
            for c, v in enumerate(row):
                if v == "#":
                    cells.append((col + c, 6 - r))
        col += len(g[0]) + 1
    occ = set(cells)
    d = s * .5  # depth offset (up-right)
    back, fronts = [], []
    # extrusions (top + right faces) first, front faces last: the front plane always covers the depth
    for (c, r) in sorted(cells, key=lambda t: (-t[0], t[1])):
        x, y = x0 + c * s, y0 - (r + 1) * s
        if (c, r + 1) not in occ:
            back.append(f'<path d="M{x:.1f} {y:.1f} l{d:.1f} {-d:.1f} h{s} l{-d:.1f} {d:.1f}Z" fill="{p["top"]}"/>')
        if (c + 1, r) not in occ:
            back.append(f'<path d="M{x + s:.1f} {y:.1f} l{d:.1f} {-d:.1f} v{s} l{-d:.1f} {d:.1f}Z" fill="{body[1]}"/>')
        fronts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{s}" height="{s}" fill="{body[0]}"/>'
                      f'<rect x="{x + .5:.1f}" y="{y + .5:.1f}" width="{s - 1}" height="{s - 1}" fill="none" stroke="{body[2]}" stroke-width="1" opacity=".5"/>')
    out = back + fronts
    # grass tufts / snow on some top faces
    rnd = random.Random(7)
    for (c, r) in cells:
        if (c, r + 1) not in occ and rnd.random() < .35:
            x, y = x0 + c * s + s * .4, y0 - (r + 1) * s - d * .4
            if st["season"] == "winter":
                continue
            out.append("".join(f'<path d="M{x + k:.1f} {y:.1f} q{k * .3:.1f} -4 {k * .7:.1f} -7" stroke="{shade(p["leaf"], .8)}" stroke-width="1.4" fill="none" stroke-linecap="round"/>' for k in (-2.5, 0, 2.5)))
    return "".join(out), col * s - s


def short_time(t):
    """'1,234 hrs 56 mins' -> '1,234 h'; '54 hrs 35 mins' -> '54h 35m'."""
    import re
    h = re.search(r"([\d,]+)\s*hr", t)
    m = re.search(r"(\d+)\s*min", t)
    if h and int(h.group(1).replace(",", "")) >= 100:
        return f"{h.group(1)} h"
    return " ".join(x for x in [f"{h.group(1)}h" if h else "", f"{m.group(1)}m" if m else ""] if x) or t


def chip(x, y, label, dark=False):
    t, w = text(label, x + 14, y + 25, 20, "#f3eee6" if dark else INK, kind="monoB")
    bg = "#ffffff" if not dark else "#2b2540"
    return f'<rect x="{x}" y="{y}" width="{w + 28:.0f}" height="36" rx="18" fill="{bg}" opacity="{.62 if not dark else .7}"/>{t}', w + 28


def coder(iso, X, Y, night):
    """A tiny figure on the island's edge: black hair, dark hoodie, laptop on the knees (clover on the lid)."""
    P = lambda x, y, z: iso.P(X + x, Y + y, z)  # noqa: E731
    d = .8 if night else 1
    out = []
    B = lambda c, *bx: out.append(ibox(P, *bx, *_C(c, d)))  # noqa: E731
    hood, jeans, skin, hair, shoe = "#3b3653", "#5d7fb0", "#f2d3b8", "#1f1b2b", "#f3eee6"
    B(jeans, .34, .66, 1, .32, .34, .12)             # thighs on the edge
    for lx in (.36, .53):
        B(jeans, lx, 1.0, .58, .11, .1, .5)          # shins over the side
        B(shoe, lx, 1.0, .5, .11, .14, .09)
    B(hood, .3, .4, 1, .4, .3, .5)                   # torso
    B(hood, .27, .38, 1.38, .46, .2, .14)            # hood bunched on the shoulders
    B(skin, .34, .44, 1.5, .32, .3, .3)              # head
    B(hair, .32, .42, 1.76, .36, .34, .1)
    B(hair, .32, .42, 1.56, .36, .08, .22)           # back of the hair
    # laptop: base on the knees, lid up facing him (we see the back of the lid)
    B("#c9cdd8", .32, .68, 1.12, .36, .26, .03)
    B("#aeb4c4", .32, .66, 1.15, .36, .03, .28)
    lx, ly = P(.5, .69, 1.29)
    out.append(f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="1.3" fill="#5fb36f"/>')
    if night:
        gx, gy = P(.5, .6, 1.45)
        out.append(f'<circle cx="{gx:.1f}" cy="{gy:.1f}" r="3.5" fill="#bfe3ff" opacity=".45" class="glow"/>')
    # legs swing a little
    return f'<g><title>Bilim, coding on the edge of the island</title>{"".join(out)}</g>'


def sky_whale(st, ox, oy, v=5.2):
    """A slow voxel whale drifting behind the island, with a tiny meadow (and a tree) growing on its back."""
    night = st["phase"] == "night"
    p = SEASONS[st["season"]]
    d = .95 if night else 1
    P = lambda x, y, z: (ox + (x - y) * v, oy + (x + y) * v / 2 - z * v)  # noqa: E731
    body, back_, belly = "#7896cf", "#5f7dba", "#e8eef9"
    out, tail = [], []
    B = lambda c, *bx: out.append(ibox(P, *bx, *_C(c, d)))  # noqa: E731
    face_y = lambda y, x0, z0, x1, z1: poly([P(x0, y, z0), P(x1, y, z0), P(x1, y, z1), P(x0, y, z1)])  # noqa: E731
    sx, sy = P(5, 4, 8)
    for k in range(3):
        out.append(f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="{v * .9:.1f}" fill="{"#dfe9f7" if not night else "#9fb4dc"}" class="spout" style="animation-delay:{k * .5:.1f}s"/>')
    B(body, 0, 1, .6, 2.2, 6, 5.6)                   # rounded snout
    B(body, 2, 0, 0, 8, 8, 7)                        # head
    B(back_, 3, 1, 7, 6.4, 6, .5)
    B(body, 10, .5, .5, 10, 7, 6)
    B(body, 20, 1.8, 1.4, 6, 4.4, 4.4)
    ax, ay = P(26, 4, 3.6)
    tail.append(ibox(P, 26, 2.8, 2.4, 4, 2.4, 2.2, *_C(body, d)))
    tail.append(ibox(P, 29, -2.2, 3.1, 2.6, 12.4, .7, *_C(back_, d)))
    out.append(f'<g class="fluke" style="transform-origin:{ax:.1f}px {ay:.1f}px">{"".join(tail)}</g>')
    bc = shade(belly, d)
    out.append(f'<path d="{face_y(7.01, 0, .6, 2.2, 2.2)}" fill="{bc}"/><path d="{face_y(8.01, 2, 0, 10, 2.4)}" fill="{bc}"/>'
               f'<path d="{face_y(7.51, 10, .5, 20, 2.2)}" fill="{bc}"/><path d="{face_y(6.21, 20, 1.4, 26, 2.4)}" fill="{bc}"/>')
    out.append(f'<path d="{face_y(8.02, 2.6, 4.2, 3.8, 5.3)}" fill="{INK}"/>')
    mx0, my0 = P(2, 8.02, 2.6); mx1, my1 = P(8, 8.02, 2.5)
    out.append(f'<path d="M{mx0:.1f} {my0:.1f} Q{(mx0 + mx1) / 2:.1f} {(my0 + my1) / 2 + 3:.1f} {mx1:.1f} {my1:.1f}" stroke="{shade(body, .55)}" stroke-width="1.4" fill="none"/>')
    fx, fy = P(9, 8, 1.6)
    out.append(f'<g class="fin" style="transform-origin:{fx:.1f}px {fy:.1f}px">{ibox(P, 8, 8, 1.2, 4, 3.4, .6, *_C(back_, d))}</g>')
    grass = mix(p["top"], "#9fd38a", .6) if st["season"] == "autumn" else p["top"]
    B(grass, 9, 1.5, 6.5, 10, 5, .7)
    B(shade(p["side"][1], 1.05), 15, 3, 7.2, 1, 1, 2.2)
    B(p["crown"] if st["season"] != "winter" else "#f4f7fd", 14, 2, 9.4, 3, 3, 2.4)
    for cx, cy in [(11, 3), (12.5, 5), (17.5, 4.5)]:
        px_, py_ = P(cx, cy, 7.2)
        out.append(f'<circle cx="{px_ - 2:.1f}" cy="{py_:.1f}" r="1.8" fill="{p["leaf"]}"/><circle cx="{px_ + 2:.1f}" cy="{py_:.1f}" r="1.8" fill="{p["leaf"]}"/>'
                   f'<circle cx="{px_:.1f}" cy="{py_ - 2:.1f}" r="1.8" fill="{p["leaf"]}"/>')
    dx_, dy_ = P(19, 6.5, 6.5)
    out.append(f'<circle cx="{dx_:.1f}" cy="{dy_:.1f}" r="1.6" fill="{p["water"]}" class="drip"/>')
    if night:
        for x, z in [(4, 1.2), (8, .9), (12.5, 1.4), (16, 1.1), (21, 2.2)]:
            gx, gy = P(x, 7.6 if x < 19 else 6.2, z + 1.4)
            out.append(f'<circle cx="{gx:.1f}" cy="{gy:.1f}" r="6" fill="url(#halo)" class="glow" style="animation-delay:{x * .3:.1f}s"/>'
                       f'<circle cx="{gx:.1f}" cy="{gy:.1f}" r="1.6" fill="#bff3ff"/>')
    return f'<g class="whale"><title>a sky whale passing by</title>{"".join(out)}</g>'


# ---------------------------------------------------------------- header
def header(st):
    W, H = 1200, 420
    rnd = random.Random(st["today"].toordinal())
    back, fore = sky_layer(st, W, H, rnd)
    world, lights, _ = build_island(st)
    night = st["phase"] == "night"
    b = [back, sky_whale(st, 548, 300, 4.6), world]
    if night:
        b.append(f'<rect width="{W}" height="{H}" fill="#141a33" opacity=".42"/>')
    elif st["phase"] == "evening":
        b.append(f'<rect width="{W}" height="{H}" fill="#f2a072" opacity=".12"/>')
    b.append(lights)
    b.append(f'<mask id="bottomfade"><linearGradient id="bf" x1="0" y1="0" x2="0" y2="1"><stop offset=".78" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
             f'<rect width="{W}" height="{H}" fill="url(#bf)"/></mask><g mask="url(#bottomfade)">{fore}</g>')
    ink = "#f3eee6" if night else INK
    sub = "#c9c4dc" if night else shade(INK, 1.9)
    nm, _ = block_name("BILIM", 66, 156, 16, st)
    b.append(nm)
    t, _ = text("fullstack developer", 70, 198, 24, ink, kind="mono"); b.append(t)
    t, _ = text("builds small worlds, one block at a time", 70, 236, 20, sub, kind="mono"); b.append(t)
    weather_word = {"sunny": "sunny", "clear": "clear", "cloudy": "cloudy", "rain": "snowing" if st["season"] == "winter" else "raining"}[st["weather"]]
    rows = [f"{weather_word} · {st['weekly']} commits this week"]
    if st["repo"]:
        rows.append(f"now building: {st['repo']}")

    if st["holiday"]:
        rows.append({"new year": "happy new year", "nooruz": "nooruz mairamy", "halloween": "spooky week"}[st["holiday"]])
    y = 270
    for r in rows:
        c, _ = chip(58, y, r, dark=night)
        b.append(c)
        y += 44
    label = f"Bilim — fullstack developer. Island level {st['level']}, {weather_word}."
    return svg(W, H, "".join(b), label, sky_colors(st))


# ---------------------------------------------------------------- cards
def card_sky(st):
    return SKY[st["phase"]] if st["phase"] in ("night",) else DAY_SKY[st["season"]]


def stats_card(st):
    W, H = 600, 340
    s = st["stats"]
    night = st["phase"] == "night"
    ink = "#f3eee6" if night else INK
    sub = "#c9c4dc" if night else shade(INK, 1.9)
    p = SEASONS[st["season"]]
    b = []
    t, _ = text("in blocks", 30, 56, 34, ink, kind="title"); b.append(t)
    t, _ = text(f"rank {s['level']}", 570, 52, 22, ink, "end", "monoB"); b.append(t)
    data = [(s["commits"], "commits"), (s["prs"], "PRs"), (s["issues"], "issues"), (s["stars"], "stars")]
    cols = [p["top"], "#b9a6e0", "#8fb8de", p["leaf"]]
    for i, (n, k) in enumerate(data):
        h = max(1, round(math.log2(n + 1) * .55))
        iso = Iso(84 + i * 140, 190, 18)
        for z in range(h):
            topc = z == h - 1
            for x in (0, 1):
                if topc:
                    iso.add(x, 0, z, cols[i])
                else:
                    iso.add(x, 0, z, *STONE)
        b.append(f'<g class="rise" style="animation-delay:{i * .15}s">{iso.render()}</g>')
        v = f"{n / 1000:.1f}K".replace(".0K", "K") if n >= 1000 else str(n)
        t, _ = text(v, 84 + i * 140 + 9, 256, 26, ink, "middle", "monoB"); b.append(t)
        t, _ = text(k, 84 + i * 140 + 9, 282, 20, sub, "middle", "mono"); b.append(t)
    nxt = st["next"]
    k = lambda n: f"{n / 1000:g}K" if n >= 1000 else str(n)
    line = f"level {st['level']} · next: {nxt[1]} @ {k(nxt[0])}" if nxt else f"level {st['level']} · all unlocked"
    t, _ = text(line, 300, 326, 20, sub, "middle", kind="mono"); b.append(t)
    return svg(W, H, "".join(b), "GitHub stats", card_sky(st))


def districts_card(st):
    W, H = 600, 340
    night = st["phase"] == "night"
    ink = "#f3eee6" if night else INK
    sub = "#c9c4dc" if night else shade(INK, 1.9)
    p = SEASONS[st["season"]]
    b = []
    t, _ = text("districts", 30, 56, 34, ink, kind="title"); b.append(t)
    t, _ = text(short_time(st["total"]), 570, 52, 22, ink, "end", "monoB"); b.append(t)
    sub_line = f"languages, {st['wrange']}"
    t, _ = text(sub_line, 30, 86, 20, sub, kind="mono"); b.append(t)
    icons = []
    # forest / lake / cliffs / meadow icons
    for i in range(4):
        iso = Iso(52, 120 + i * 54, 12)
        if i == 0:
            iso.add(0, 0, 0, shade(p["side"][1], 1.05)); iso.add(0, 0, 1, p["crown"])
        elif i == 1:
            iso.add(0, 0, 0, p["water"])
        elif i == 2:
            iso.add(0, 0, 0, "#c9c3cf"); iso.add(0, 0, 1, "#c9c3cf")
        else:
            iso.add(0, 0, 0, p["top"])
        icons.append(iso.render())
    names = ["forest", "lake", "cliffs", "meadow"]
    order_icon = {0: 0, 1: 1, 2: 2, 3: 3}
    for i, (name, pct, hrs) in enumerate(st["langs"][:4]):
        y = 140 + i * 54
        b.append(icons[order_icon[i]])
        t, _ = text(f"{name}", 92, y, 22, ink, kind="monoB"); b.append(t)
        t, nw = text(names[i], 92 + 230, y, 20, sub, kind="mono"); b.append(t)
        t, _ = text(f"{pct:.0f}% · {hrs:.0f}h", 570, y, 20, ink, "end", "monoB"); b.append(t)
    return svg(W, H, "".join(b), "Languages as island districts", card_sky(st))


def garden_footer(st):
    W, H = 1200, 150
    p = SEASONS[st["season"]]
    night = st["phase"] == "night"
    ink = "#f3eee6" if night else INK
    sub = "#c9c4dc" if night else shade(INK, 1.9)
    b = []
    iso = Iso(1046, 70 if st["lucky"] else 54, 18)
    for x in range(4):
        for y in range(3):
            iso.add(x, y, 0, p["top"], p["side"][0], p["side"][1])
    iso.add(1, 1, -1, *STONE)
    iso.add(2, 1, -1, *STONE)
    plants = ""
    n = min(st["found"], 12)
    for k in range(n):
        gx, gy = .5 + (k % 4) * .9 + .2, .5 + (k // 4) * .8
        px, py = iso.P(gx, gy, 1)
        newest = st["lucky"] and k == n - 1
        if newest:
            plants += f'<circle cx="{px:.0f}" cy="{py - 20:.0f}" r="56" fill="url(#halo)" class="glow"/>'
        plants += f'<g class="sway2">{standing_clover(px, py, 8 if newest else 6, p["leaf"], 4, 26 if newest else 16)}</g>'
    if not n:
        plants = iso.flat_clover(2, 1.5, 1, .6, shade(p["top"], .85), 3)
    b.append(f'<g class="bob">{iso.render()}{plants}</g>')
    if st["lucky"]:
        cx, cy = iso.P(2, 1.5, 1)
        b += [sparkle(cx - 60, cy - 40, 7, 0), sparkle(cx + 60, cy - 50, 6, -.7), sparkle(cx + 70, cy - 10, 4, -1.3)]
        msg = "a four-leaf clover grew in the garden today"
    else:
        msg = "three leaves today. one day in ten, it's four"
    t, _ = text(msg, 40, 70, 24, ink, kind="monoB" if st["lucky"] else "mono"); b.append(t)
    t, _ = text(f"clover garden: {st['found']}   ·   {SEASONS[st['season']]['tag']}", 40, 108, 20, sub, kind="mono"); b.append(t)
    return svg(W, H, "".join(b), "Clover garden — daily luck", card_sky(st))


def divider():
    W, H = 1200, 36
    iso = Iso(600, 6, 9)
    iso.add(0, 0, 0, "#a9d8a0")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
            f'<path d="M150 18 H560 M640 18 H1050" stroke="#6b6680" stroke-width="1.4" stroke-dasharray="2 8" stroke-linecap="round"/>{iso.render()}</svg>')


# ---------------------------------------------------------------- link buttons (one svg per link, so each can be a link)
ICONS = {
    # generic glyphs, not brand logos: paper plane, briefcase, camera
    "telegram": '<path d="M2 11 L20 3 L15 20 L10 14 Z" fill="none" stroke="{c}" stroke-width="2" stroke-linejoin="round"/><path d="M10 14 L20 3" stroke="{c}" stroke-width="2"/>',
    "linkedin": '<rect x="2" y="7" width="18" height="12" rx="2" fill="none" stroke="{c}" stroke-width="2"/><path d="M8 7 V4 H14 V7 M2 12 H20" fill="none" stroke="{c}" stroke-width="2"/>',
    "instagram": '<rect x="2" y="3" width="18" height="17" rx="5" fill="none" stroke="{c}" stroke-width="2"/><circle cx="11" cy="11.5" r="4" fill="none" stroke="{c}" stroke-width="2"/><circle cx="16" cy="7" r="1.3" fill="{c}"/>',
}


def link_button(kind, handle, st):
    """A raised block with the handle on its face; depth goes up-right like the block name."""
    p = SEASONS[st["season"]]
    _, tw = text(handle, 0, 0, 20, "#000", kind="monoB")
    H, d = 72, 10
    w = round(52 + tw + 20)
    W = w + d + 10
    x, y, h = 4, d + 4, H - d - 10
    face, side, edge = "#f6efe6", "#4a4270", "#2b2540"
    out = [f'<path d="M{x} {y} l{d} {-d} h{w} l{-d} {d}Z" fill="{p["top"]}"/>',
           f'<path d="M{x + w} {y} l{d} {-d} v{h} l{-d} {d}Z" fill="{side}"/>',
           f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{face}" stroke="{edge}" stroke-width="2"/>']
    out.append(f'<g transform="translate({x + 16} {y + h / 2 - 11})">{ICONS[kind].format(c=edge)}</g>')
    t, tw = text(handle, x + 52, y + h / 2 + 7, 20, edge, kind="monoB")
    out.append(t)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{kind}: {handle}">'
            f'<title>{kind}: {handle}</title>{"".join(out)}</svg>')


def time_card(st):
    """All-time coding total (public WakaTime badge) as a big number built from blocks."""
    import re
    W, H = 600, 340
    night = st["phase"] == "night"
    ink = "#f3eee6" if night else INK
    sub = "#c9c4dc" if night else shade(INK, 1.9)
    p = SEASONS[st["season"]]
    m = re.search(r"([\d,]+)\s*hr", st.get("all_time", "") or "")
    hours = m.group(1) if m else "0"
    b = []
    t, _ = text("at the keyboard", 30, 56, 34, ink, kind="title"); b.append(t)
    t, _ = text("all time, by WakaTime", 30, 86, 20, sub, kind="mono"); b.append(t)
    word = hours + " H"
    cols = sum(len(PIXEL[c][0]) + 1 for c in word) - 1
    s_ = min(12, int(520 / cols))
    num, nw = block_name(word, (W - cols * s_) / 2, 230, s_, st)
    b.append(num)
    h_int = int(hours.replace(",", "") or 0)
    days = h_int / 24
    t, _ = text(f"≈ {days:.0f} days of pure coding", W / 2, 300, 20, sub, "middle", "mono"); b.append(t)
    return svg(W, H, "".join(b), f"{hours} hours of coding, all time", card_sky(st))


# ---------------------------------------------------------------- rhythm: when the commits happen (replaces the WakaTime languages card)
def rhythm_card(st):
    """24 iso columns, one per hour of the day (Bishkek time), height = commits in that hour.
    The strip behind the columns is the sky at that hour; the island's own day/night colours."""
    W, H = 600, 340
    night = st["phase"] == "night"
    ink = "#f3eee6" if night else INK
    sub = "#c9c4dc" if night else shade(INK, 1.9)
    p = SEASONS[st["season"]]
    hours = st.get("hours") or [0] * 24
    top = max(hours) or 1
    peak = max(range(24), key=lambda h: hours[h]) if any(hours) else None
    nightly = sum(hours[h] for h in list(range(22, 24)) + list(range(0, 6)))
    morning = sum(hours[h] for h in range(6, 11))
    total = sum(hours)
    if not total:
        title = "rhythm"
    elif nightly / total >= .3:
        title = "night owl"
    elif morning / total >= .3:
        title = "early bird"
    else:
        title = "daytime coder"
    b = []
    t, _ = text(title, 30, 56, 34, ink, kind="title"); b.append(t)
    t, _ = text("when the commits happen" + (f" · peak {peak:02d}:00" if peak is not None else ""), 30, 86, 20, sub, kind="mono"); b.append(t)
    # sky strip: night -> dawn -> day -> dusk -> night
    stops = [(0, "#1d2242"), (5, "#2c2f5c"), (7, "#f2b38f"), (10, "#cfe3ee"), (16, "#d9e9f0"), (19, "#f2a072"), (21, "#4a3f78"), (24, "#1d2242")]
    grad = "".join(f'<stop offset="{h / 24:.3f}" stop-color="{c}"/>' for h, c in stops)
    x0, x1, base = 36, 564, 250
    b.append(f'<linearGradient id="daysky" x1="0" x2="1">{grad}</linearGradient>'
             f'<rect x="{x0}" y="{base + 2}" width="{x1 - x0}" height="12" rx="6" fill="url(#daysky)"/>')
    # columns
    step = (x1 - x0) / 24
    iso = Iso(0, 0, step * .42)
    cols = []
    for h in range(24):
        n = hours[h]
        hgt = 0 if not n else max(1, round(n / top * 7))
        cx = x0 + step * (h + .5)
        sub_iso = Iso(cx, base - step * .21, step * .42)
        is_night = h >= 22 or h < 6
        colr = "#8f86c9" if is_night else p["top"]
        for z in range(hgt):
            c = colr if z == hgt - 1 else STONE[0]
            if z == hgt - 1:
                sub_iso.add(0, 0, z, c)
            else:
                sub_iso.add(0, 0, z, *STONE)
        cols.append(f'<g class="rise" style="animation-delay:{h * .03:.2f}s">{sub_iso.render()}</g>')
    b.append("".join(cols))
    # moon / sun markers and hour ticks
    for h, lab in [(0, "00"), (6, "06"), (12, "12"), (18, "18"), (23, "23")]:
        t, _ = text(lab, x0 + step * (h + .5), base + 38, 20, sub, "middle", "mono"); b.append(t)
    if peak is not None:  # soft glow behind the busiest hour
        px = x0 + step * (peak + .5)
        b.insert(3, f'<circle cx="{px:.0f}" cy="{base - 50}" r="46" fill="url(#halo)" class="glow"/>')
    streak, best = st.get("streak", 0), st.get("best_streak", 0)
    t, _ = text(f"streak {streak} days  ·  best {best}", 30, 324, 20, ink, kind="monoB"); b.append(t)
    return svg(W, H, "".join(b), f"{title}: commit hours", card_sky(st))


# ---------------------------------------------------------------- archipelago: every public repo is its own little floating island
LANG_COLORS = {"TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Python": "#3572A5", "Vue": "#41b883", "HTML": "#e34c26",
               "CSS": "#663399", "SCSS": "#c6538c", "C++": "#f34b7d", "Go": "#00ADD8", "Rust": "#dea584", None: "#9aa0a6"}


def archipelago_card(st):
    """Full-width card: the latest public repos as floating islands in a row."""
    W, H = 1200, 340
    night = st["phase"] == "night"
    ink = "#f3eee6" if night else INK
    sub = "#c9c4dc" if night else shade(INK, 1.9)
    p = SEASONS[st["season"]]
    repos = (st.get("repos") or [])[:4]
    b = []
    t, _ = text("archipelago", 40, 58, 34, ink, kind="title"); b.append(t)
    t, _ = text("one island per repo · roof = language · size = commits", 40, 90, 20, sub, kind="mono"); b.append(t)
    if not repos:
        return svg(W, H, "".join(b), "archipelago", card_sky(st))
    top_c = max(r["commits"] for r in repos) or 1
    n_r = len(repos)
    for i, r in enumerate(repos):
        cx = W * (i + .5) / n_r
        n = 2 if r["commits"] < top_c * .3 else (3 if r["commits"] < top_c * .7 else 4)
        s_ = 16
        iso = Iso(cx, 172 + (4 - n) * s_ * .5, s_)
        off = -(n - 1) / 2
        for x in range(n):
            for y in range(n):
                iso.add(x, y, 0, p["top2"] if (x + y + i) % 5 == 0 else p["top"], p["side"][0], p["side"][1])
        for z, k in [(-1, 0), (-2, 1)]:
            for x in range(k, n - k):
                for y in range(k, n - k):
                    iso.add(x, y, z, shade(p["side"][0], .92 - .08 * -z), shade(p["side"][0], .8), shade(p["side"][1], .75))
        lc = LANG_COLORS.get(r.get("lang"), LANG_COLORS[None])
        floors = 1 + min(2, int(math.log10(max(r.get("size", 1), 10))) - 1)
        hx = hy = 0 if n < 3 else 1
        for z in range(1, floors + 1):
            iso.add(hx, hy, z, "#f3ece4", "#ddd1c4", "#c5b6a6")
            iso.put((hx, hy, z), f'<path d="{iso.face(hx, hy, z, "px", .3, .25, .7, .7)}" fill="{"#ffd98a" if night else "#5a6078"}"/>')
        iso.add(hx, hy, floors + 1, lc)
        if r.get("stars"):
            fx, fy = iso.P(n - .5, n - .5, 1)
            iso.put((n - 1, n - 1, 0), f'<path d="M{fx:.1f} {fy:.1f} v-30" stroke="{INK}" stroke-width="2.2"/>'
                                      f'<path d="M{fx:.1f} {fy - 30:.1f} l18 6 l-18 6z" fill="#ffd884" stroke="{INK}" stroke-width="1.4"/>')
        b.append(f'<g class="{"bob" if i % 2 == 0 else "bob2"}">{iso.render()}</g>')
        name = r["name"] if len(r["name"]) <= 18 else r["name"][:17] + "…"
        t, _ = text(name, cx, 282, 22, ink, "middle", "monoB"); b.append(t)
        meta = f"{(r.get('lang') or '-').lower()} · {r['commits']}" + (f" ·  {r['stars']}" if r.get("stars") else "")
        t, mw = text(meta, cx + 9, 314, 20, sub, "middle", "mono"); b.append(t)
        if r.get("stars"):
            cw = mw / len(meta); i0 = meta.rindex("  ") + .5
            sx, sy = cx + 9 - mw / 2 + cw * (i0 + .5), 307
            pts = " ".join(f"{sx + (6.5 if k % 2 == 0 else 2.8) * math.sin(k * math.pi / 5):.1f},{sy - (6.5 if k % 2 == 0 else 2.8) * math.cos(k * math.pi / 5):.1f}" for k in range(10))
            b.append(f'<polygon points="{pts}" fill="#e8b04a"/>')
        b.append(f'<circle cx="{cx - mw / 2 - 3:.0f}" cy="{307}" r="6" fill="{lc}"/>')
    return svg(W, H, "".join(b), "archipelago of repositories", card_sky(st))


GREENS = ["#d5ecbf", "#a9d891", "#78c06c", "#46a05a"]


def terrain_card(st):
    """Full-width card: the last year of contributions as a strip of land.
    Each day is a column (height = contributions), empty days are water, the best day grows a lucky clover."""
    W, H = 1200, 390
    night = st["phase"] == "night"
    ink = "#f3eee6" if night else INK
    sub = "#c9c4dc" if night else shade(INK, 1.9)
    cal = st.get("calendar") or {}
    days = cal.get("days") or []
    b = []
    t, _ = text("a year of land", 40, 58, 34, ink, kind="title"); b.append(t)
    t, _ = text("a block per day · empty days are water", 40, 90, 20, sub, kind="mono"); b.append(t)
    if not days:
        return svg(W, H, "".join(b), "a year of contributions", card_sky(st))

    from datetime import date as _d
    first = _d.fromisoformat(days[0][0])
    off = (first.weekday() + 1) % 7            # GitHub weeks start on Sunday
    cells = {}
    for i, (ds, c) in enumerate(days):
        k = i + off
        cells[(k // 7, k % 7)] = (ds, c)
    weeks = max(x for x, _ in cells) + 1
    top_c = max(c for _, c in days) or 1
    best = max(days, key=lambda d: d[1])[0]

    vx, vy, hz, uy = -11.5, 8.2, 15, 1.7
    ux = (W - 90 - 7 * -vx) / weeks
    ox = 45 + 7 * -vx
    oy = 168

    def P(x, y, z):
        return ox + x * ux + y * vx, oy + x * uy + y * vy - z * hz

    def lvl(c):
        return 0 if c == 0 else 1 + min(3, int(4 * c / (top_c + 1)))

    heights = [0.28, 1.0, 1.7, 2.6, 3.7]
    snow = st["season"] == "winter"
    dim = .62 if night else 1
    water = shade("#7cc3ea", .55 if night else 1)
    out, deco = [], []
    for x in range(weeks):
        for y in range(7):
            cells.setdefault((x, y), ("", 0))
    rock, rock2 = shade("#a98068", dim * .9), shade("#a98068", dim * .72)
    out.append(f'<path d="{poly([P(0, 7, 0), P(weeks, 7, 0), P(weeks, 7, -.9), P(0, 7, -.9)])}" fill="{rock}"/>')
    out.append(f'<path d="{poly([P(weeks, 0, 0), P(weeks, 7, 0), P(weeks, 7, -.9), P(weeks, 0, -.9)])}" fill="{rock2}"/>')
    for (x, y) in sorted(cells, key=lambda c: (c[0] + c[1], c[0])):
        ds, c = cells[(x, y)]
        L = lvl(c)
        z = heights[L]
        top = water if L == 0 else shade(("#f4f7fd" if snow and L >= 3 else GREENS[L - 1]), dim)
        side = shade(top, .84) if L == 0 else shade("#c99c78", dim * (1 - .03 * L))
        right = shade(side, .82)
        out.append(f'<path d="{poly([P(x, y + 1, 0), P(x + 1, y + 1, 0), P(x + 1, y + 1, z), P(x, y + 1, z)])}" fill="{side}"/>')
        out.append(f'<path d="{poly([P(x + 1, y, 0), P(x + 1, y + 1, 0), P(x + 1, y + 1, z), P(x + 1, y, z)])}" fill="{right}"/>')
        if L:   # grass lip on the sides
            g = shade(GREENS[L - 1] if not (snow and L >= 3) else "#f4f7fd", dim * .9)
            lip = max(z - .35, 0)
            out.append(f'<path d="{poly([P(x, y + 1, lip), P(x + 1, y + 1, lip), P(x + 1, y + 1, z), P(x, y + 1, z)])}" fill="{g}"/>')
            out.append(f'<path d="{poly([P(x + 1, y, lip), P(x + 1, y + 1, lip), P(x + 1, y + 1, z), P(x + 1, y, z)])}" fill="{shade(g, .85)}"/>')
        out.append(f'<path d="{poly([P(x, y, z), P(x + 1, y, z), P(x + 1, y + 1, z), P(x, y + 1, z)])}" fill="{top}"/>')
        cx, cy = P(x + .5, y + .5, z)
        if ds == best and c:
            out.append(f'<circle cx="{cx:.1f}" cy="{cy - 14:.1f}" r="22" fill="url(#halo)" class="glow"/>')
            out.append(standing_clover(cx, cy, 7, "#5fbf6a", 4, 16))
            deco.append(sparkle(cx + 12, cy - 26, 5, .4))
        elif L == 4:
            out.append(standing_clover(cx, cy, 4.5, shade("#5fb36f", dim), 3, 9))
        elif L == 0 and (x * 7 + y) % 11 == 3:
            out.append(f'<path d="M{cx - 4:.1f} {cy:.1f} h8" stroke="#ffffff" stroke-opacity=".6" stroke-width="1.6" stroke-linecap="round" class="tw" style="animation-delay:{(x % 5) * .7:.1f}s"/>')
        if ds == days[-1][0]:
            fx, fy = cx, cy
    # today: a small flag
    deco.append(f'<path d="M{fx:.1f} {fy:.1f} v-34" stroke="{ink}" stroke-width="2.2"/>'
                f'<path d="M{fx:.1f} {fy - 34:.1f} l18 6 l-18 6z" fill="#ffd884" stroke="{INK}" stroke-width="1.4"/>')
    b.append("".join(out) + "".join(deco))

    # month labels along the front edge
    seen = set()
    for (x, y), (ds, _) in sorted(cells.items()):
        m = ds[:7]
        if y == 0 and ds and ds[8:] <= "07" and m not in seen and x > 0:
            seen.add(m)
            lx, ly = P(x + .5, 7, 0)
            t, _ = text(_d.fromisoformat(ds).strftime("%b").lower(), lx, ly + 36, 16, sub, "middle", "mono"); b.append(t)

    # numbers, top right
    total, cur, longest = cal.get("total", sum(c for _, c in days)), cal.get("streak", 0), cal.get("longest", 0)
    x = W - 40
    for val, lab in [(f"{longest}d", "best streak"), (f"{cur}d", "streak"), (f"{total:,}", "this year")]:
        t, lw = text(lab, x, 90, 18, sub, "end", "mono"); b.append(t)
        t, vw = text(val, x, 58, 30, ink, "end", "monoB"); b.append(t)
        x -= max(lw, vw) + 34
    return svg(W, H, "".join(b), "a year of contributions as land", card_sky(st))


def _ago(iso_ts, now):
    from datetime import datetime, timezone
    t = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    m = int((now - t).total_seconds() // 60)
    if m < 60:
        return f"{max(m, 1)}m ago"
    if m < 60 * 24:
        return f"{m // 60}h ago"
    d = m // (60 * 24)
    return "yesterday" if d == 1 else f"{d}d ago"


def train_card(st, now=None):
    """Full-width card: a little voxel train, one wagon per recent commit, rolling through the meadow."""
    from datetime import datetime, timezone
    now = now or datetime.now(timezone.utc)
    W, H = 1200, 384
    night = st["phase"] == "night"
    ink = "#f3eee6" if night else INK
    sub = "#c9c4dc" if night else shade(INK, 1.9)
    p = SEASONS[st["season"]]
    commits = (st.get("commits") or [])[:4]
    k = 19.0
    ox, oy = 120, 196

    def P(x, y, z):
        return ox + x * k - y * .35 * k, oy + y * .68 * k - z * .95 * k

    def box(x, y, z, dx, dy, dz, top, front=None, right=None, extra=""):
        front, right = front or shade(top, .84), right or shade(top, .7)
        return (f'<path d="{poly([P(x, y, z + dz), P(x + dx, y, z + dz), P(x + dx, y + dy, z + dz), P(x, y + dy, z + dz)])}" fill="{top}"{extra}/>'
                f'<path d="{poly([P(x, y + dy, z), P(x + dx, y + dy, z), P(x + dx, y + dy, z + dz), P(x, y + dy, z + dz)])}" fill="{front}"{extra}/>'
                f'<path d="{poly([P(x + dx, y, z), P(x + dx, y + dy, z), P(x + dx, y + dy, z + dz), P(x + dx, y, z + dz)])}" fill="{right}"{extra}/>')

    def wheel(x, r=.48):
        cx, cy = P(x, 2.62, .42)
        R = r * k
        return (f'<g class="spin"><circle cx="{cx:.1f}" cy="{cy:.1f}" r="{R:.1f}" fill="#3a3350" stroke="#c9b48a" stroke-width="2"/>'
                f'<path d="M{cx - R + 3:.1f} {cy:.1f} H{cx + R - 3:.1f} M{cx:.1f} {cy - R + 3:.1f} V{cy + R - 3:.1f}" stroke="#c9b48a" stroke-width="1.6"/></g>'
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="2.2" fill="#c9b48a"/>')

    dim = .65 if night else 1
    grass = shade(mix(p["top"], "#9fd38a", .6) if st["season"] == "autumn" else p["top"], dim)
    earth = shade(p["side"][0], dim)
    period = 6
    dxp, dyp = period * k, 0
    css = (f'<style>.roll{{animation:roll 2.4s linear infinite}}@keyframes roll{{to{{transform:translate({-dxp:.1f}px,{-dyp:.1f}px)}}}}'
           '.spin{transform-box:fill-box;transform-origin:center;animation:spin .9s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}'
           '.puff{transform-box:fill-box;transform-origin:center;animation:puff 2.4s ease-out infinite;opacity:0}'
           '@keyframes puff{0%{transform:translate(0,0) scale(.4);opacity:.85}100%{transform:translate(-64px,-26px) scale(1.8);opacity:0}}'
           '.rum{animation:rum .35s ease-in-out infinite alternate}@keyframes rum{to{transform:translateY(1.2px)}}'
           '@media (prefers-reduced-motion: reduce){.roll,.spin,.puff,.rum{animation:none}.puff{opacity:.5}}</style>')
    b = [css]
    # ground: a long strip of meadow, with ties and tufts sliding past
    b.append(f'<path d="{poly([P(-12, -3, 0), P(80, -3, 0), P(80, 6, 0), P(-12, 6, 0)])}" fill="{grass}"/>')
    b.append(f'<path d="{poly([P(-12, 6, 0), P(80, 6, 0), P(80, 6, -.9), P(-12, 6, -.9)])}" fill="{earth}"/>')
    b.append(f'<path d="{poly([P(-12, .1, .01), P(80, .1, .01), P(80, 3.1, .01), P(-12, 3.1, .01)])}" fill="{shade("#b8a48c", dim)}"/>')
    rnd = random.Random(11)
    pattern = []
    for _ in range(7):
        pattern.append((rnd.uniform(0, period), rnd.choice([-2.4, -1.4, 3.8, 4.6, 5.4]), rnd.random() < .4))
    roll = []
    for base in range(-12, 80, period):
        for t in range(0, period * 2, 3):
            x = base + t / 2
            roll.append(box(x, .25, 0, .55, 2.7, .12, shade("#8a6a52", dim), shade("#6f533f", dim), shade("#5c4433", dim)))
        for (dx, y, clover) in pattern:
            cx, cy = P(base + dx, y, 0)
            if clover:
                roll.append(standing_clover(cx, cy, 4.2, shade(p["leaf"], dim), 3, 10))
            else:
                roll.append(f'<path d="M{cx - 5:.1f} {cy:.1f} l2 -8 l2 6 l2 -9 l2 9 l2 -6" stroke="{shade(p["leaf"], dim * .8)}" stroke-width="1.6" fill="none" stroke-linecap="round"/>')
    b.append(f'<g class="roll">{"".join(roll)}</g>')
    for y in (.75, 2.15):
        b.append(f'<path d="{poly([P(-12, y, .22), P(80, y, .22), P(80, y + .14, .22), P(-12, y + .14, .22)])}" fill="#d5d0dc"/>')
        b.append(f'<path d="{poly([P(-12, y + .14, .1), P(80, y + .14, .1), P(80, y + .14, .22), P(-12, y + .14, .22)])}" fill="#8f8aa0"/>')

    # wagons (oldest at the back / left), locomotive at the front / right
    xs = 0.0
    train, labels = [], []
    for i, c in enumerate(reversed(commits)):
        lc = LANG_COLORS.get(c.get("lang"), LANG_COLORS[None])
        a = xs
        if i:
            cx0, cy0 = P(a - 1.5, 1.5, .75); cx1, cy1 = P(a, 1.5, .75)
            train.append(f'<path d="M{cx0:.1f} {cy0:.1f} L{cx1:.1f} {cy1:.1f}" stroke="#3a3350" stroke-width="3"/>')
        train.append(box(a, .45, .45, 9, 2.15, .45, shade("#7a5a46", dim)))
        train.append(box(a + .15, .5, .9, 8.7, 2.05, .55, shade("#c98f5e", dim)))
        h = int(hashlib.sha256(c.get("oid", c["msg"]).encode()).hexdigest(), 16)
        crates = 1 + h % 3
        for j in range(crates):
            cx_ = a + .6 + j * 2.8
            hh = 1.1 + ((h >> (4 + j)) % 3) * .35
            train.append(box(cx_, .75, 1.45, 2.3, 1.6, hh, shade(lc, dim), shade(lc, dim * .82), shade(lc, dim * .66)))
            tx, ty = P(cx_ + 1.15, 2.35, 1.45 + hh / 2)
            train.append(f'<path d="M{tx - 6:.1f} {ty:.1f} h12" stroke="#ffffff" stroke-opacity=".55" stroke-width="2"/>')
        if (h >> 9) % 4 == 0:
            cx_, cy_ = P(a + 8.1, 1.6, 1.45)
            train.append(standing_clover(cx_, cy_, 4.5, "#6cc47a", 4, 12))
        for wx in (a + 1.3, a + 2.5, a + 6.5, a + 7.7):
            train.append(wheel(wx))
        # label under the wagon
        lx, ly = P(a + 4.5, 6, -.9)
        repo = c["repo"] if len(c["repo"]) <= 16 else c["repo"][:15] + "…"
        msg = c["msg"] if len(c["msg"]) <= 16 else c["msg"][:15].rstrip() + "…"
        t, _ = text(repo, lx, ly + 30, 18, ink, "middle", "monoB"); labels.append(t)
        t, _ = text(msg, lx, ly + 53, 16, sub, "middle", "mono"); labels.append(t)
        t, _ = text(_ago(c["date"], now), lx, ly + 74, 15, sub, "middle", "mono"); labels.append(t)
        xs += 10.6
    # locomotive
    a = xs
    if commits:
        cx0, cy0 = P(a - 1.5, 1.5, .75); cx1, cy1 = P(a, 1.5, .75)
        train.append(f'<path d="M{cx0:.1f} {cy0:.1f} L{cx1:.1f} {cy1:.1f}" stroke="#3a3350" stroke-width="3"/>')
    g, g2 = shade("#4f9a5e", dim), shade("#3c7a49", dim)
    train.append(box(a, .45, .45, 8.6, 2.15, .5, shade("#3a3350", dim)))
    train.append(box(a, .4, .95, 2.8, 2.25, 2.9, g2))                        # cab
    wx0, wy0 = P(a + .7, 2.65, 2.4)
    win = "#ffd98a" if night else "#cfe6f0"
    train.append(f'<path d="{poly([P(a + .6, 2.65, 2.2), P(a + 2.2, 2.65, 2.2), P(a + 2.2, 2.65, 3.25), P(a + .6, 2.65, 3.25)])}" fill="{win}"/>')
    train.append(box(a - .25, .25, 3.85, 3.3, 2.55, .3, shade("#2f2a44", dim)))   # roof
    train.append(box(a + 2.8, .6, .95, 5.0, 1.85, 1.9, g))                     # boiler
    for bx in (a + 4.2, a + 6.2):
        train.append(f'<path d="{poly([P(bx, 2.45, .95), P(bx + .25, 2.45, .95), P(bx + .25, 2.45, 2.85), P(bx, 2.45, 2.85)])}" fill="#e3c37a"/>')
    train.append(box(a + 6.0, 1.15, 2.85, .8, .8, 1.3, shade("#2f2a44", dim)))  # chimney
    smx, smy = P(a + 6.4, 1.55, 4.3)
    for d in range(3):
        b_col = "#e9e6f0" if not night else "#8d88a6"
        train.append(f'<circle cx="{smx:.1f}" cy="{smy - 4:.1f}" r="10" fill="{b_col}" class="puff" style="animation-delay:{d * .8:.1f}s"/>')
    lx_, ly_ = P(a + 7.8, 2.0, 1.9)
    lampx, lampy = P(a + 7.8, 1.5, 1.6)
    train.append(f'<circle cx="{P(a + 7.8, 1.5, 1.9)[0]:.1f}" cy="{P(a + 7.8, 1.5, 1.9)[1]:.1f}" r="5" fill="#ffd98a" stroke="#3a3350" stroke-width="1.5"/>')
    train.append(box(a + 7.8, .5, .95, .5, 2.05, .4, shade("#c9b48a", dim)))   # buffer
    if night:
        hx, hy = P(a + 7.9, 1.5, 1.9)
        train.insert(0, f'<path d="M{hx:.1f} {hy:.1f} L{hx + 260:.1f} {hy - 30:.1f} L{hx + 260:.1f} {hy + 50:.1f}Z" fill="url(#beam)"/>')
    for wx in (a + 1.4, a + 3.6, a + 5.4, a + 7.2):
        train.append(wheel(wx, .55 if wx > a + 3 else .48))
    b.append(f'<defs><linearGradient id="beam"><stop offset="0" stop-color="#ffe6a3" stop-opacity=".55"/><stop offset="1" stop-color="#ffe6a3" stop-opacity="0"/></linearGradient></defs>')
    b.append(f'<g class="rum">{"".join(train)}</g>')
    b.extend(labels)

    t, _ = text("commit express", 40, 58, 34, ink, kind="title"); b.append(t)
    t, _ = text("one wagon per commit · cargo = language", 40, 90, 20, sub, kind="mono"); b.append(t)
    nxt = st.get("next")
    kk = lambda n: f"{n / 1000:g}K" if n >= 1000 else str(n)  # noqa: E731
    stop = f"next stop: {nxt[1]}" if nxt else "last stop: the castle"
    t, _ = text(stop, W - 40, 58, 22, ink, "end", "monoB"); b.append(t)
    if nxt:
        t, _ = text(f"at {kk(nxt[0])} commits", W - 40, 90, 18, sub, "end", "mono"); b.append(t)
    return svg(W, H, "".join(b), "recent commits as a little train", card_sky(st))


# ---------------------------------------------------------------- daily chest
LOOT = [  # name, rarity, weight
    ("mushroom", "common", 32), ("apple", "common", 32), ("scroll", "common", 28), ("carrot", "common", 28),
    ("bone", "uncommon", 20), ("potion", "uncommon", 16), ("clover", "uncommon", 16),
    ("crystal", "rare", 11), ("golden bone", "rare", 9),
    ("crown", "legendary", 3),
]
RARITY = {"common": "#a9a3b8", "uncommon": "#5fb36f", "rare": "#4f8fe0", "legendary": "#e6a832"}

SPRITES = {
    "mushroom": ["...kkkk...", "..krrwrk..", ".krwrrrrk.", "krrrrrwrrk", "kkkkkkkkkk", "...kwwk...", "...kwwk...", "...kwwk...", "..kwwwwk..", "...kkkk..."],
    "apple": [".....kg...", "....kgk...", "..kkkkkk..", ".krrrrrrk.", "krhrrrrrrk", "krhrrrrrrk", "krrrrrrrrk", "krrrrrrrrk", ".krrrrrrk.", "..kkkkkk.."],
    "scroll": ["kkkkkkkkkk", "kyyyyyyyyk", "kkkkkkkkkk", ".kppppppk.", ".kpllllpk.", ".kppppppk.", ".kpllllpk.", "kkkkkkkkkk", "kyyyyyyyyk", "kkkkkkkkkk"],
    "carrot": ["...g..g...", "....gg....", "..kkkkkk..", "..kooook..", "..kowook..", "...kook...", "...kook...", "....kk....", "....k.....", ".........."],
    "bone": ["..........", "..........", ".kk....kk.", "kwwkkkkwwk", ".kwwwwwwk.", ".kwwwwwwk.", "kwwkkkkwwk", ".kk....kk.", "..........", ".........."],
    "golden bone": ["..........", "..........", ".kk....kk.", "kyykkkkyyk", ".kyhyyyyk.", ".kyyyyyyk.", "kyykkkkyyk", ".kk....kk.", "..........", ".........."],
    "potion": ["...kkkk...", "...kcck...", "....kk....", "...kbbk...", "..kbbbbk..", ".kvvvvvvk.", ".kvwvvvvk.", ".kvvvvvvk.", "..kvvvvk..", "...kkkk..."],
    "clover": ["...kkk....", "..kgggk...", "..kgdgk...", "kkkkgkkkk.", "kgggkgggk.", "kgdgkgdgk.", ".kkk.kkk..", "....k.....", "....k.....", ".........."],
    "crystal": ["....kk....", "...kwck...", "..kwccck..", ".kwcccdck.", "kwcccdcdck", ".kccccddk.", "..kccddk..", "...kcdk...", "....kk....", ".........."],
    "crown": ["..........", "k...k...k.", "kk.kyk.kk.", "kykyyykyk.", "kyyyyyyyk.", "kyryybyyk.", "kyyyyyyyk.", "kooooooook", "kkkkkkkkk.", ".........."],
}
SPRITE_PAL = {"k": "#2b2540", "r": "#e0574c", "w": "#fff3e6", "h": "#ffb0a8", "g": "#5fb36f", "d": "#3f8a4e", "y": "#ffd25a",
              "p": "#f3e2b3", "l": "#c9a66b", "o": "#f08a3c", "b": "#cfe6f0", "v": "#b07ae0", "c": "#7ee0e0", "e": "#e6a832"}
SPRITE_PAL_ITEM = {"scroll": {"y": "#b9805a"}, "potion": {"c": "#b9805a"}, "crown": {"o": "#e6a832", "b": "#6aa8e8"}, "golden bone": {"h": "#fff1b8"}}


def sprite(name, x, y, px, silhouette=False, night=False):
    pal = dict(SPRITE_PAL, **SPRITE_PAL_ITEM.get(name, {}))
    out = []
    for r, row in enumerate(SPRITES[name]):
        c = 0
        while c < len(row):
            ch = row[c]
            if ch == ".":
                c += 1
                continue
            n = 1
            while c + n < len(row) and row[c + n] == ch:
                n += 1
            col = ("#8b86a3" if night else "#c9c3d8") if silhouette else pal[ch]
            out.append(f'<rect x="{x + c * px:.1f}" y="{y + r * px:.1f}" width="{n * px + .3:.1f}" height="{px + .3:.1f}" fill="{col}"/>')
            c += n
    return "".join(out)


def loot(day_iso):
    h = int(hashlib.sha256(f"chest:{day_iso}".encode()).hexdigest(), 16) % sum(w for *_, w in LOOT)
    for name, rar, w in LOOT:
        if h < w:
            return name, rar
        h -= w


def chest_card(st):
    """Full-width card: one chest per day; a commit opens it. The dog guards it.
    The collection is rebuilt from the contribution calendar, so nothing has to be stored."""
    W, H = 1200, 360
    night = st["phase"] == "night"
    ink = "#f3eee6" if night else INK
    sub = "#c9c4dc" if night else shade(INK, 1.9)
    p = SEASONS[st["season"]]
    days = (st.get("calendar") or {}).get("days") or []
    today = days[-1][0] if days else st["today"].isoformat()
    opened = bool(days) and days[-1][1] > 0
    item, rar = loot(today)
    got = {}
    for ds, c in days:
        if c:
            n, _ = loot(ds)
            got[n] = got.get(n, 0) + 1
    mood = dog_mood(st)
    b = []

    # --- little floating meadow with the dog and the chest
    v = 8.4
    ox, oy = 250, 132
    P = lambda x, y, z: (ox + (x - y) * v, oy + (x + y) * v / 2 - z * v)  # noqa: E731
    d = .75 if night else 1
    grass = mix(p["top"], "#9fd38a", .6) if st["season"] == "autumn" else p["top"]
    scene = [ibox(P, -1, -4, -3.2, 24, 20, 1.6, shade(p["side"][0], .9 * d), shade(p["side"][0], .78 * d), shade(p["side"][1], .74 * d)),
             ibox(P, -3, -6, -1.6, 28, 24, 1.6, shade(grass, d), shade(p["side"][0], d), shade(p["side"][1], d))]
    rnd = random.Random(8)
    for _ in range(14):
        tx, ty = P(rnd.uniform(-2, 24), rnd.uniform(-5, 17), 0)
        if True:
            scene.append(f'<path d="M{tx - 4:.1f} {ty:.1f} q1 -6 2 -9 M{tx:.1f} {ty:.1f} v-11 M{tx + 4:.1f} {ty:.1f} q-1 -6 -2 -9" '
                         f'stroke="{shade(p["leaf"], .85 * d)}" stroke-width="1.6" fill="none" stroke-linecap="round"/>')
    wood, gold = "#a8693d", "#e3b04b"
    chest = []
    cx0, cy0 = 12, -3
    gt, gpy, gpx = _C(gold, d)

    def bands(y0, dy, z0, dz):   # gold straps: only the faces that can be seen
        for bx in (cx0 + .7, cx0 + 8.4):
            chest.append(f'<path d="{poly([P(bx, y0, z0 + dz), P(bx + .9, y0, z0 + dz), P(bx + .9, y0 + dy, z0 + dz), P(bx, y0 + dy, z0 + dz)])}" fill="{gt}"/>'
                         f'<path d="{poly([P(bx, y0 + dy, z0), P(bx + .9, y0 + dy, z0), P(bx + .9, y0 + dy, z0 + dz), P(bx, y0 + dy, z0 + dz)])}" fill="{gpy}"/>')
        chest.append(f'<path d="{poly([P(cx0 + 10, y0, z0), P(cx0 + 10, y0 + dy, z0), P(cx0 + 10, y0 + dy, z0 + dz), P(cx0 + 10, y0, z0 + dz)])}" fill="none"/>')
    if opened:
        chest.append(ibox(P, cx0, cy0 - 1.4, 6, 10, 1.4, 6.4, *_C(shade(wood, 1.1), d)))           # lid, thrown back
        bands(cy0 - 1.45, 1.5, 6, 6.5)
    chest.append(ibox(P, cx0, cy0, 0, 10, 6, 6, *_C(wood, d)))
    if opened:
        chest.append(f'<path d="{poly([P(cx0 + .6, cy0 + .6, 6.01), P(cx0 + 9.4, cy0 + .6, 6.01), P(cx0 + 9.4, cy0 + 5.4, 6.01), P(cx0 + .6, cy0 + 5.4, 6.01)])}" fill="#3a2418"/>')
        bands(cy0 - .05, 6.1, 0, 6.05)
    else:
        chest.append(ibox(P, cx0, cy0, 6, 10, 6, 2.6, *_C(shade(wood, 1.12), d)))
        bands(cy0 - .05, 6.1, 0, 8.65)
    chest.append(ibox(P, cx0 + 4.3, cy0 + 6, 4.2, 1.4, .5, 2.2, *_C(gold, d)))                # lock
    kx, ky = P(cx0 + 5, cy0 + 6.5, 5)
    chest.append(f'<rect x="{kx - 1.5:.1f}" y="{ky - 2:.1f}" width="3" height="5" fill="#5a3a22"/>')
    scene.append(dog(P, v, mood, night))
    scene.append("".join(chest))
    scene.append(dog_friends(P, v, mood, night, opened, cx0, cy0))
    sx, sy = P(-1.2, 16.5, 0)
    plank = "#c99a6a" if not night else "#8f6e50"
    t, nw = text(DOG_NAME, sx, sy - 30, 17, INK, "middle", "monoB")
    scene.append(f'<rect x="{sx - 2.5:.1f}" y="{sy - 44:.1f}" width="5" height="44" fill="{shade(plank, .7)}"/>'
                 f'<rect x="{sx - nw / 2 - 10:.1f}" y="{sy - 50:.1f}" width="{nw + 20:.1f}" height="28" rx="4" fill="{plank}" stroke="{shade(plank, .65)}" stroke-width="2"/>{t}')
    if opened:
        ix, iy = P(cx0 + 5, cy0 + 3, 15)
        scene.append(f'<circle cx="{ix:.1f}" cy="{iy:.1f}" r="58" fill="url(#halo)" class="glow"/>'
                     f'<g class="hover">{sprite(item, ix - 25, iy - 25, 5)}</g>'
                     + sparkle(ix - 36, iy - 18, 6, 0) + sparkle(ix + 34, iy - 4, 5, .8) + sparkle(ix + 18, iy - 38, 4, 1.5))
    else:
        qx, qy = P(cx0 + 5, cy0 + 3, 14)
        t, _ = text("?", qx, qy + 12, 40, sub, "middle", "monoB")
        scene.append(f'<g class="hover">{t}</g>')
    b.append(f'<g class="bob">{"".join(scene)}</g>')

    # --- text + collection
    t, _ = text("daily chest", 600, 58, 34, ink, kind="title"); b.append(t)
    if opened:
        t, w = text(f"today: {item}", 600, 92, 20, ink, kind="monoB"); b.append(t)
        t, _ = text(f"· {rar}", 600 + w + 10, 92, 20, RARITY[rar], kind="mono"); b.append(t)
    else:
        t, _ = text("closed · a commit today opens it", 600, 92, 20, sub, kind="mono"); b.append(t)
    found = sum(got.values())
    t, _ = text(f"{found} found", W - 40, 58, 20, sub, "end", "mono"); b.append(t)
    for i, (name, rar_, _) in enumerate(LOOT):
        col, row = i % 5, i // 5
        x, y = 600 + col * 112, 122 + row * 112
        n = got.get(name, 0)
        b.append(f'<rect x="{x}" y="{y}" width="100" height="100" rx="12" fill="{"#ffffff" if not night else "#2c2f5a"}" fill-opacity="{.45 if not night else .55}"/>')
        b.append(f'<rect x="{x + 38}" y="{y + 90}" width="24" height="4" rx="2" fill="{RARITY[rar_]}"/>')
        b.append(sprite(name, x + 30, y + 14, 4, silhouette=not n, night=night))
        t, _ = text(f"×{n}" if n else "???", x + 50, y + 80, 18, ink if n else sub, "middle", "monoB" if n else "mono"); b.append(t)
    return svg(W, H, "".join(b), "daily chest with a dog guarding it", card_sky(st))


# ---------------------------------------------------------------- languages (GitHub, private repos included)
def _lang_rows(st, k=6):
    d = st.get("langs_gh") or {}
    rows = sorted(d.get("langs", []), key=lambda r: -r["bytes"])
    total = sum(r["bytes"] for r in rows) or 1
    top, rest = rows[:k], rows[k:]
    out = [dict(r, pct=100 * r["bytes"] / total, color=r.get("color") or LANG_COLORS.get(r["name"], LANG_COLORS[None])) for r in top]
    if rest:
        out.append({"name": "other", "bytes": sum(r["bytes"] for r in rest), "pct": 100 * sum(r["bytes"] for r in rest) / total,
                    "color": "#b9b3c6", "repos": None})
    return out, d


def _size(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {u}" if u == "B" else f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} TB"


FOSSILS = {  # tiny things buried in each layer (a pun per language). k = dark, w = bone, a/b = accents
    "python": ["..www....", ".w...w...", ".....w...", "...ww....", "..w......", ".w....w..", "..wwww..."],
    "typescript": ["...k.....", "..kak....", ".kaabk...", "kaaabbk..", ".kabbk...", "..kbk....", "...k....."],
    "javascript": ["..aaaa...", ".aaakaa..", "aakkkaa..", "aaakaaa..", ".aaaaa...", "..aaa....", "........."],
    "vue": ["ka.....ak", ".ka...ak.", "..ka.ak..", "...kak...", "....k....", ".........", "........."],
    "html": ["kkkkkkkk.", "kaakaaak.", "kkkkkkkk.", "kaaakaak.", "kkkkkkkk.", ".........", "........."],
    "css": ["...a.....", "..aaa....", ".aaaaa...", ".aawaa...", ".aaaaa...", "..aaa....", "........."],
    "dockerfile": [".....w...", "..kk.k...", "kkkkkk...", "kaaaaaak.", ".kaaaaak.", "..kkkkk..", "........."],
    "shell": ["...kk....", "..kwak...", ".kwawak..", "kwawawak.", ".kkkkkk..", ".........", "........."],
}


def _fossil(name, x, y, px, layer):
    if name.lower() == "python":   # a snake skeleton: wavy spine, ribs, skull
        bone, dk = "#f4ecda", shade(layer, .45)
        L = 13 * px
        out = [f'<path d="M{x:.1f} {y + 4 * px:.1f} q{L / 8:.1f} {-2.5 * px:.1f} {L / 4:.1f} 0 t{L / 4:.1f} 0 t{L / 4:.1f} 0 t{L / 4:.1f} 0" stroke="{bone}" stroke-width="{px:.1f}" fill="none" stroke-linecap="round"/>']
        for k in range(1, 12):
            rx_ = x + k * L / 12
            ph = math.sin(k / 12 * 4 * math.pi) * -1.25 * px
            out.append(f'<path d="M{rx_:.1f} {y + 4 * px + ph - 1.6 * px:.1f} v{3.2 * px:.1f}" stroke="{bone}" stroke-width="{px * .55:.1f}" opacity=".9"/>')
        out.append(f'<ellipse cx="{x + L + 1.6 * px:.1f}" cy="{y + 4 * px:.1f}" rx="{2 * px:.1f}" ry="{1.4 * px:.1f}" fill="{bone}"/>'
                   f'<circle cx="{x + L + 2.2 * px:.1f}" cy="{y + 3.6 * px:.1f}" r="{px * .45:.1f}" fill="{dk}"/>')
        return f'<g opacity=".9"><title>a python fossil</title>{"".join(out)}</g>'
    rows = FOSSILS.get(name.lower())
    if not rows:
        return ""
    pal = {"k": shade(layer, .45), "w": "#f4ecda", "a": shade(layer, 1.35), "b": shade(layer, .8)}
    out = []
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            if ch != ".":
                out.append(f'<rect x="{x + c * px:.1f}" y="{y + r * px:.1f}" width="{px + .2:.1f}" height="{px + .2:.1f}" fill="{pal[ch]}"/>')
    return f'<g opacity=".85"><title>a {name.lower()} fossil</title>{"".join(out)}</g>'


def strata_card(st):
    """Full width: a cut through the island, every layer of rock is a language (thickness = share of code)."""
    W, H = 1200, 430
    night = st["phase"] == "night"
    ink = "#f3eee6" if night else INK
    sub = "#c9c4dc" if night else shade(INK, 1.9)
    p = SEASONS[st["season"]]
    rows, d = _lang_rows(st)
    b = []
    t, _ = text("what it's made of", 40, 58, 34, ink, kind="title"); b.append(t)
    n_rep, n_priv = d.get("repos", 0), d.get("private", 0)
    t, _ = text(f"a cut through the island · {n_rep} repos, {n_priv} of them private", 40, 90, 20, sub, kind="mono"); b.append(t)
    if not rows:
        return svg(W, H, "".join(b), "languages as layers of the island", card_sky(st))
    s = 16
    iso = Iso(236, 150, s)
    P = iso.P
    dim = .85 if night else 1
    total_h, mins = 9.6, .6
    hs = [max(mins, total_h * r["pct"] / 100) for r in rows]
    hs = [h * total_h / sum(hs) for h in hs]
    X, Y = 7, 4.4
    out, front = [], []
    rnd = random.Random(3)
    # floating pebbles around the block
    for (fx, fy, fz, sz) in [(-2.6, 2, -3, .9), (-1.5, 4.5, -1.6, .55), (-3.2, 6, -8.4, .55), (9.6, 1, -10.5, .5)]:
        front.append(f'<g class="bob" style="animation-delay:{fx:.1f}s">{ibox(P, fx, fy, fz, sz, sz, sz * .8, *_C(shade(p["side"][1], .9), dim))}</g>')
    # rocky tip, vines and a crystal underneath
    out.append(ibox(P, 1.2, .8, -total_h - 1.4, 4.6, 2.8, 1.4, *_C(shade(p["side"][1], .8), dim)))
    out.append(ibox(P, 2.6, 1.5, -total_h - 2.5, 2, 1.4, 1.1, *_C(shade(p["side"][1], .7), dim)))
    cx_, cy_ = P(3.6, 2.9, -total_h - 2.5)
    out.append(f'<path d="M{cx_ - 4:.1f} {cy_:.1f} l4 12 l4 -12z" fill="#9fe3e8" opacity=".9"/><path d="M{cx_ + 3:.1f} {cy_ - 1:.1f} l3 8 l3 -8z" fill="#7ccfe0"/>')
    for (vx, vy) in [(.6, 4.4), (3.0, 4.4), (5.6, 4.4), (7, 2.2)]:
        a, bq = P(vx, vy, -total_h)
        ln = 22 + (vx * 7) % 18
        out.append(f'<path d="M{a:.1f} {bq:.1f} q4 {ln / 2:.0f} -1 {ln:.0f}" stroke="{shade(p["leaf"], .8 * dim)}" stroke-width="1.8" fill="none" class="sway2"/>'
                   f'<circle cx="{a - 1:.1f}" cy="{bq + ln:.1f}" r="2" fill="{shade(p["leaf"], dim)}"/>')
    dx_, dy_ = P(3.6, 2.9, -total_h - 2.5)
    out.append(f'<circle cx="{dx_:.1f}" cy="{dy_ + 14:.1f}" r="1.8" fill="{p["water"]}" class="drip"/>')
    z = 0.0
    mids = []
    for li, (r, h) in enumerate(zip(rows, hs)):
        z0 = -z - h
        c = mix(r["color"], "#efe6d8", .18)
        top_, py_, px_ = _C(c, dim)
        out.append(f'<path d="{poly([P(0, Y, z0), P(X, Y, z0), P(X, Y, z0 + h), P(0, Y, z0 + h)])}" fill="{py_}"/>'
                   f'<path d="{poly([P(X, 0, z0), P(X, Y, z0), P(X, Y, z0 + h), P(X, 0, z0 + h)])}" fill="{px_}"/>')
        lr = random.Random(r["name"])
        # sediment lines
        for k in range(int(h * 1.6)):
            zz = z0 + h * (k + 1) / (int(h * 1.6) + 1)
            a0, a1, a2 = P(0, Y, zz), P(X, Y, zz + lr.uniform(-.08, .08)), P(X, 0, zz + lr.uniform(-.08, .08))
            out.append(f'<path d="M{a0[0]:.1f} {a0[1]:.1f} L{a1[0]:.1f} {a1[1]:.1f} L{a2[0]:.1f} {a2[1]:.1f}" stroke="{shade(c, .7)}" stroke-width="1" fill="none" opacity=".35" stroke-dasharray="{lr.randint(10, 30)} {lr.randint(4, 12)}"/>')
        for _ in range(int(2 + h * 3)):
            if lr.random() < .5:
                qx, qy = P(lr.uniform(.3, X - .3), Y, lr.uniform(z0 + .15, z0 + h - .15))
            else:
                qx, qy = P(X, lr.uniform(.3, Y - .3), lr.uniform(z0 + .15, z0 + h - .15))
            out.append(f'<ellipse cx="{qx:.1f}" cy="{qy:.1f}" rx="{lr.uniform(1.5, 3):.1f}" ry="1.4" fill="{shade(c, .6)}" opacity=".45"/>')
        # the fossil of this language, if the layer is thick enough
        if h * s >= 15:
            fx, fy = P(lr.uniform(1.2, X - 2.6), Y, z0 + h / 2)
            out.append(_fossil(r["name"], fx - 8, fy - 6 + 5, 2 if h * s < 26 else 2.6, c))
        out.append(f'<path d="M{P(0, Y, z0)[0]:.1f} {P(0, Y, z0)[1]:.1f} L{P(X, Y, z0)[0]:.1f} {P(X, Y, z0)[1]:.1f} L{P(X, 0, z0)[0]:.1f} {P(X, 0, z0)[1]:.1f}" stroke="{shade(c, .55)}" stroke-width="1.2" fill="none" opacity=".6"/>')
        if li == 0:   # a small mine in the top layer: tunnel, rails and a lantern
            m0, m1 = P(X, 2.4, z0 + .25), P(X, 3.6, z0 + .25)
            tx_, ty_ = P(X, 3.0, z0 + .25)
            out.append(f'<path d="M{m0[0]:.1f} {m0[1]:.1f} L{m1[0]:.1f} {m1[1]:.1f} L{m1[0]:.1f} {m1[1] - 18:.1f} Q{tx_:.1f} {ty_ - 30:.1f} {m0[0]:.1f} {m0[1] - 18:.1f}Z" fill="#241c2e"/>')
            lx_, ly_ = P(X, 2.15, z0 + 1.35)
            out.append(f'<circle cx="{lx_:.1f}" cy="{ly_:.1f}" r="{14 if night else 9}" fill="url(#halo)" class="glow"/>'
                       f'<rect x="{lx_ - 2.5:.1f}" y="{ly_ - 3:.1f}" width="5" height="6" rx="1" fill="#ffd884" stroke="#5a3a22" stroke-width="1"/>')
            # roots of the tree reaching into the top layer
            for rx_, rl in [(4.8, 1.3), (5.6, 1.0), (6.3, 1.5)]:
                r0 = P(rx_, Y, 0)
                r1 = P(rx_ + .3, Y, -rl)
                out.append(f'<path d="M{r0[0]:.1f} {r0[1]:.1f} Q{r0[0] - 4:.1f} {(r0[1] + r1[1]) / 2:.1f} {r1[0]:.1f} {r1[1]:.1f}" stroke="{shade(p["side"][1], .7)}" stroke-width="1.6" fill="none" opacity=".8"/>')
        mids.append(z0 + h / 2)
        z += h
    gx, gy = P(1.6, Y, -total_h + .4)
    out.append(f'<g><title>a bone keko buried</title><path d="M{gx - 7:.1f} {gy:.1f} h14" stroke="#ffd25a" stroke-width="3" stroke-linecap="round"/>'
               + "".join(f'<circle cx="{gx + dx:.1f}" cy="{gy + dy:.1f}" r="1.8" fill="#ffd25a"/>' for dx in (-8, 8) for dy in (-1.6, 1.6)) + '</g>')
    # top: grass, tree, flowers, a clover, a little signpost
    grass = mix(p["top"], "#9fd38a", .6) if st["season"] == "autumn" else p["top"]
    out.append(ibox(P, 0, 0, 0, X, Y, .6, *_C(grass, dim)))
    out.append(ibox(P, 5, 1.2, .6, .5, .5, 1.8, *_C(shade(p["side"][1], 1.05), dim)))
    crown = p["crown"] if st["season"] != "winter" else "#f4f7fd"
    out.append(ibox(P, 4.3, .5, 2.3, 1.9, 1.9, 1.5, *_C(crown, dim)))
    out.append(ibox(P, 4.8, 1, 3.8, 1, 1, .7, *_C(shade(crown, 1.06), dim)))
    for (fx, fy) in [(1.2, 3.4), (2.9, 3.9), (6.4, 3.6), (.8, 1.4)]:
        qx, qy = P(fx, fy, .6)
        out.append(f'<path d="M{qx:.1f} {qy:.1f} v-6" stroke="{shade(p["leaf"], .8)}" stroke-width="1.3"/><circle cx="{qx:.1f}" cy="{qy - 7:.1f}" r="2.2" fill="{["#f5a9bf", "#ffd884", "#ffffff", "#c9a7f0"][int(fx * 3) % 4]}"/>')
    cx_, cy_ = P(2.2, 2.2, .6)
    out.append(f'<g class="sway2">{standing_clover(cx_, cy_, 6, p["leaf"], 4, 14)}</g>')
    sx_, sy_ = P(.9, 3.1, .6)
    out.append(f'<rect x="{sx_ - 1.2:.1f}" y="{sy_ - 18:.1f}" width="2.4" height="18" fill="#7a5a46"/><path d="M{sx_ - 13:.1f} {sy_ - 22:.1f} h22 l5 5 l-5 5 h-22z" fill="#c99a6a" stroke="#7a5a46" stroke-width="1"/>')
    t, _ = text("code", sx_ - 2, sy_ - 13, 9, INK, "middle", "monoB"); out.append(t)
    b.append(f'<g class="bob">{"".join(out)}{"".join(front)}</g>')
    # labels: leader line, colour, name, a little bar, share, size and repos
    ys = [P(X, Y / 2, m)[1] for m in mids]
    gap = 36
    lab = list(ys)
    lab[0] = max(lab[0], 148)
    for i in range(1, len(lab)):
        lab[i] = max(lab[i], lab[i - 1] + gap)
    shift = max(0, lab[-1] - (H - 30))
    lab = [y - shift for y in lab]
    for i in range(len(lab) - 2, -1, -1):
        lab[i] = min(lab[i], lab[i + 1] - gap)
    top_pct = rows[0]["pct"] or 1
    for r, y0, y1 in zip(rows, ys, lab):
        ex, _ = P(X, Y / 2, 0)
        b.append(f'<path d="M{ex + 4:.1f} {y0:.1f} C{ex + 70:.1f} {y0:.1f} {450:.1f} {y1:.1f} {505:.1f} {y1:.1f} H530" stroke="{sub}" stroke-width="1.4" fill="none" opacity=".7"/>'
                 f'<circle cx="{ex + 4:.1f}" cy="{y0:.1f}" r="2.5" fill="{sub}"/>')
        b.append(f'<rect x="538" y="{y1 - 9:.1f}" width="18" height="18" rx="4" fill="{r["color"]}"/>')
        t, _ = text(r["name"].lower(), 568, y1 + 7, 21, ink, kind="monoB"); b.append(t)
        bw = 150 * r["pct"] / top_pct
        b.append(f'<rect x="736" y="{y1 - 4:.1f}" width="130" height="8" rx="4" fill="{sub}" opacity=".18"/>'
                 f'<rect x="736" y="{y1 - 4:.1f}" width="{max(bw * 130 / 150, 4):.1f}" height="8" rx="4" fill="{r["color"]}"/>')
        t, _ = text(f'{r["pct"]:.1f}%', 960, y1 + 7, 21, ink, "end", "monoB"); b.append(t)
        meta = _size(r["bytes"]) + (f' · {r["repos"]}' if r.get("repos") else "")
        t, mw = text(meta, 1160, y1 + 7, 18, sub, "end", "mono"); b.append(t)
    t, _ = text("size · repos", 1160, 120, 15, sub, "end", "mono"); b.append(t)
    return svg(W, H, "".join(b), "languages as layers of the island", card_sky(st))


def districts_gh_card(st):
    """Full width: a square plot of 100 tiles, 1 tile = 1% of all code; each language is a district with houses."""
    W, H = 1200, 360
    night = st["phase"] == "night"
    ink = "#f3eee6" if night else INK
    sub = "#c9c4dc" if night else shade(INK, 1.9)
    p = SEASONS[st["season"]]
    rows, d = _lang_rows(st)
    b = []
    t, _ = text("districts", 40, 58, 34, ink, kind="title"); b.append(t)
    t, _ = text(f"1 tile = 1% of the code · {d.get('repos', 0)} repos, private too", 40, 90, 20, sub, kind="mono"); b.append(t)
    if not rows:
        return svg(W, H, "".join(b), "languages as districts", card_sky(st))
    # largest remainder → exactly 100 tiles
    raw = [r["pct"] for r in rows]
    cnt = [int(x) for x in raw]
    for i in sorted(range(len(raw)), key=lambda i: -(raw[i] - cnt[i]))[:100 - sum(cnt)]:
        cnt[i] += 1
    owner = []
    for i, c in enumerate(cnt):
        owner += [i] * c
    # fill the 10x10 plot in a snake by diagonals so districts stay in one piece
    order = [(x, y) for x in range(10) for y in (range(10) if x % 2 == 0 else range(9, -1, -1))]
    tile = {c: owner[k] for k, c in enumerate(order)}
    iso = Iso(330, 150, 15)
    dim = .85 if night else 1
    for x in range(10):
        for y in range(10):
            iso.add(x, y, -1, *_C(shade(p["side"][0], .95), dim))
    for (x, y), i in tile.items():
        c = mix(rows[i]["color"], "#ffffff", .12)
        iso.add(x, y, 0, *_C(c, dim))
    # houses: about one per 6 tiles of a district, roofs in the language colour
    rnd = random.Random(7)
    for i in range(len(rows)):
        cells = [c for c, o in tile.items() if o == i]
        rnd.shuffle(cells)
        for (x, y) in cells[:max(1, len(cells) // 6) if rows[i]["name"] != "other" else 0]:
            hgt = 1 + (rnd.random() < .35)
            for zz in range(1, hgt + 1):
                iso.add(x, y, zz, *_C("#f3eee6" if not night else "#cfc8dc", dim))
            iso.add(x, y, hgt + 1, *_C(rows[i]["color"], dim))
            iso.put((x, y, 1), "")
    b.append(f'<g class="bob">{iso.render()}</g>')
    # legend
    y = 140
    for r, c in zip(rows, cnt):
        b.append(f'<rect x="680" y="{y - 13}" width="18" height="18" rx="4" fill="{r["color"]}"/>')
        t, _ = text(r["name"].lower(), 712, y + 3, 21, ink, kind="monoB"); b.append(t)
        t, _ = text(f'{c} tile{"s" if c != 1 else ""}', 1010, y + 3, 20, sub, "end", "mono"); b.append(t)
        t, _ = text(_size(r["bytes"]), 1160, y + 3, 20, ink, "end", "monoB"); b.append(t)
        y += 31
    return svg(W, H, "".join(b), "languages as districts", card_sky(st))
