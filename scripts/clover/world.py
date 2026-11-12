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
                rare=rare, unlocked=unlocked, next=nxt, langs=langs, total=waka.get("total", ""), repo=latest_repo,
                lucky=lucky_today, found=found, level=commits // 100)


def sky_colors(st):
    sky = SKY[st["phase"]] or DAY_SKY[st["season"]]
    if st["weather"] in ("cloudy", "rain") and st["phase"] != "night":
        sky = (mix(sky[0], "#9aa3b5", .45 if st["weather"] == "rain" else .25), mix(sky[1], "#9aa3b5", .45 if st["weather"] == "rain" else .25))
    return sky


# ---------------------------------------------------------------- the island
def build_island(st, ox=860, oy=140, s=20):
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
        for z, w in [(1, 0), (2, 0), (3, 0)]:
            iso.add(hx, hy, z, "#4f9a62", "#3f7f50", "#33693f")
        for z in (1, 2, 3):
            for k in range(3):
                cx, cy = iso.P(hx + rnd.uniform(.2, .9), hy + 1, z + rnd.uniform(.2, .8))
                lights.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="2.4" fill="{rnd.choice(["#ffd98a", "#f5a9bf", "#9fd0ec"])}" class="tw" style="animation-delay:{-rnd.uniform(0, 2):.1f}s"/>')
        sx_, sy_ = iso.P(hx + .5, hy + .5, 4.2)
        lights.append(sparkle(sx_, sy_, 8, fill="#ffd98a"))
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
        depth = 300
        wf = f'<path d="M{a0[0]:.1f} {a0[1]:.1f} L{a1[0]:.1f} {a1[1]:.1f} L{a1[0]:.1f} {a1[1] + depth:.1f} L{a0[0]:.1f} {a0[1] + depth:.1f}Z" fill="{p["water"]}" opacity=".85"/>'
        for k in range(5):
            xk = a0[0] + (a1[0] - a0[0]) * (k + .5) / 5
            yk = a0[1] + (a1[1] - a0[1]) * (k + .5) / 5
            wf += f'<path d="M{xk:.1f} {yk:.1f} V{yk + depth:.1f}" stroke="#ffffff" stroke-width="1.6" stroke-dasharray="10 18" class="pour" style="animation-delay:{-k * .27:.2f}s" opacity=".75"/>'
        front.append(wf)
        if "rainbow" in st["rare"]:
            cx, cy = (a0[0] + a1[0]) / 2, a1[1] + 120
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

    # balloon
    extra_air = ""
    if "balloon" in U:
        bxx, byy = ox - 220, oy + 10
        extra_air = (f'<g class="fly"><path d="M{bxx} {byy} c-26 0 -30 -40 0 -46 c30 6 26 46 0 46z" fill="#e98d8d" stroke="{INK}" stroke-width="1.5"/>'
                     f'<path d="M{bxx} {byy - 46} v46" stroke="{INK}" stroke-width="1" opacity=".4"/>'
                     f'<path d="M{bxx - 6} {byy} l2 10 M{bxx + 6} {byy} l-2 10" stroke="{INK}" stroke-width="1.2"/>'
                     f'<rect x="{bxx - 6}" y="{byy + 10}" width="12" height="8" rx="2" fill="#c99a6a" stroke="{INK}" stroke-width="1.2"/></g>')
    # fireflies on summer nights
    if night and st["season"] in ("summer", "spring"):
        for k in range(10):
            fx, fy = iso.P(rnd.uniform(0, 9), rnd.uniform(0, 9), rnd.uniform(1, 3))
            lights.append(f'<circle cx="{fx:.0f}" cy="{fy:.0f}" r="2" fill="#f7f3a0" class="tw" style="animation-delay:{-rnd.uniform(0, 2):.1f}s"/>')

    world = f'<g class="bob">{"".join(under)}{body}{islet_markup}{"".join(front)}</g>{extra_air}'
    return world, "".join(lights), iso


def sky_layer(st, W, H, rnd):
    """Weather and sky decoration drawn behind/in front of the island."""
    back, fore = [], []
    p = SEASONS[st["season"]]
    night = st["phase"] == "night"
    if night:
        for _ in range(60):
            x, y = rnd.uniform(0, W), rnd.uniform(0, H * .55)
            back.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{rnd.choice([.8, 1, 1.3])}" fill="#fff" class="tw" style="animation-delay:{-rnd.uniform(0, 3):.1f}s;animation-duration:{rnd.uniform(2, 5):.1f}s"/>')
        back.append(f'<circle cx="{W - 120}" cy="78" r="22" fill="#f4f1e6"/><circle cx="{W - 110}" cy="72" r="20" fill="{SKY["night"][0]}" opacity=".9"/>')
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


def chip(x, y, label, dark=False):
    t, w = text(label, x + 14, y + 25, 20, "#f3eee6" if dark else INK, kind="monoB")
    bg = "#ffffff" if not dark else "#2b2540"
    return f'<rect x="{x}" y="{y}" width="{w + 28:.0f}" height="36" rx="18" fill="{bg}" opacity="{.62 if not dark else .7}"/>{t}', w + 28


# ---------------------------------------------------------------- header
def header(st):
    W, H = 1200, 420
    rnd = random.Random(st["today"].toordinal())
    back, fore = sky_layer(st, W, H, rnd)
    world, lights, _ = build_island(st)
    night = st["phase"] == "night"
    b = [back, world]
    if night:
        b.append(f'<rect width="{W}" height="{H}" fill="#141a33" opacity=".42"/>')
    elif st["phase"] == "evening":
        b.append(f'<rect width="{W}" height="{H}" fill="#f2a072" opacity=".12"/>')
    b.append(lights)
    b.append(fore)
    ink = "#f3eee6" if night else INK
    sub = "#c9c4dc" if night else shade(INK, 1.9)
    t, _ = text("Bilim", 64, 150, 108, ink, kind="title"); b.append(t)
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
    t, _ = text(st["total"], 570, 52, 20, ink, "end", "monoB"); b.append(t)
    t, _ = text("languages, last 30 days", 30, 86, 20, sub, kind="mono"); b.append(t)
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
