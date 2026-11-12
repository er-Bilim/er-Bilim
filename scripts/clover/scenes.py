"""The four pictures: seasonal header, daily-luck footer, stats card, languages clover."""
import math
import random

import ink
from ink import INK, PAPER, FILTERS, STYLE
from hand import bilim, write, measure

DARK_INK, DARK_PAPER = "#d9d9d9", "#0d1117"
LIGHT_INK, LIGHT_PAPER = "#1f2328", "#ffffff"


def _svg(W, H, body, label, defs=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{label}">\n'
            f'  <title>{label}</title>\n  <defs>\n    {FILTERS}\n    {defs}\n    {STYLE}\n  </defs>\n{body}\n</svg>\n')


def _paper_card(W, H, inner, rx=16):
    return (f'  <clipPath id="card"><rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="{rx}"/></clipPath>\n'
            f'  <g clip-path="url(#card)">\n    <rect width="{W}" height="{H}" fill="{PAPER}"/>\n    {inner}\n'
            f'    <rect width="{W}" height="{H}" filter="url(#grain)" opacity=".07"/>\n  </g>\n'
            f'  <rect x="1.5" y="1.5" width="{W - 3}" height="{H - 3}" rx="{rx}" fill="none" stroke="{INK}" stroke-width="3"/>')


# ------------------------------------------------------------------ header
def header(season):
    W, H = 1200, 420
    rnd = random.Random(5)
    p = []
    name, dots = bilim(140, 262, 1.08, 3)
    p.append(name)
    for x, y in dots:
        p.append(ink.star5(x, y, 11, rnd, sw=1.6, fill=INK, cls="soft", dur=rnd.uniform(3, 4.5)))
    for x, y, r, f in [(92, 70, 11, "none"), (560, 84, 9, "none"), (600, 150, 6, INK), (70, 210, 7, INK),
                       (640, 246, 10, "none"), (690, 60, 7, "none"), (1150, 64, 10, "none"), (760, 170, 6, INK)]:
        p.append(ink.star5(x, y, r, rnd, fill=f, dur=rnd.uniform(2.5, 5)))
    for x, y, r in [(640, 110, 9), (1110, 150, 7), (470, 60, 7)]:
        p.append(ink.sparkle(x, y, r, rnd, dur=rnd.uniform(2, 3.5)))

    cx, cy = 930, 182
    p.append(ink.glow(cx, cy, rnd))
    stem = ink.line_pts((cx - 2, cy + 8), (cx - 26, cy + 150), rnd, .8, 30, 22)
    lucky = f'<path d="{ink.d(stem, False)}" fill="none" stroke="{INK}" stroke-width="1.9" stroke-linecap="round"/>'
    lucky += ink.watercolour_clover(cx, cy, 80, 4, rnd, "hl")
    p.append(f'<g class="bob">{lucky}</g>')
    for x, y, r in [(1036, 96, 11), (842, 112, 7), (1046, 258, 6)]:
        p.append(ink.sparkle(x, y, r, rnd, dur=rnd.uniform(2.4, 3.6)))

    srnd = random.Random(77)
    if season == "winter":
        p.append(ink.falling(W, H, srnd, "snow", 40))
    if season == "autumn":
        p.append(ink.falling(W, H, srnd, "leaf", 9))
    p.append(ink.meadow(W, H + 8, 80, 21, (8, 12), season, solid_p=.15, sw=1.5))
    if season == "winter":
        p.append(ink.snowdrift(W, H + 2, srnd))
    p.append(ink.meadow(W, H + 10, 46, 12, (13, 19), season, solid_p=.35, sw=2))
    if season == "summer":
        p.append(ink.bee(330, 330, srnd))
    if season == "spring":
        p.append(ink.bee(700, 300, srnd))
    return _svg(W, H, _paper_card(W, H, "".join(p)), "Bilim")


# ------------------------------------------------------------------ footer: daily luck
def footer(mode, lucky_today, found, season):
    ink_c, paper = (DARK_INK, DARK_PAPER) if mode == "dark" else (LIGHT_INK, LIGHT_PAPER)
    W, H = 1200, 170
    rnd = random.Random(44)
    p = []
    for i, (x, y, r) in enumerate([(240, 96, 6), (560, 84, 5), (1010, 100, 4)]):
        p.append(ink.star5(x, y, r, rnd, sw=1.3, ink=ink_c, fill=(ink_c if i % 2 else "none"), dur=rnd.uniform(2.5, 4.5)))
    note = "found a four-leaf clover today!" if lucky_today else "no four-leaf clover today. maybe tomorrow"
    t, _ = write(note, 60, 52, 15, random.Random(3), ink=ink_c, width=1.5)
    p.append(f'<g opacity=".85">{t}</g>')
    t, _ = write(f"four-leaf clovers found so far: {found}", 1140, 52, 13, random.Random(4), ink=ink_c, width=1.3, anchor="end")
    p.append(f'<g opacity=".6">{t}</g>')
    meadow = ink.meadow(W, H + 4, 70, 9, (7, 12), season, ink=ink_c, paper=paper, solid_p=.25, sw=1.5)
    if lucky_today:
        lx = 380 + random.Random(found).uniform(0, 440)
        lrnd = random.Random(found * 7 + 1)
        stem = ink.line_pts((lx, H + 4), (lx + 4, H - 74), lrnd, .5, 14, 5)
        lucky = (ink.glow(lx + 4, H - 78, lrnd, rx=52, ry=46, ticks=False)
                 + f'<path d="{ink.d(stem, False)}" fill="none" stroke="{ink_c}" stroke-width="1.6" stroke-linecap="round"/>'
                 + ink.watercolour_clover(lx + 4, H - 78, 22, 4, lrnd, "fl", sw=1.3).replace(INK, ink_c))
        for dx, dy, r in [(-26, -30, 5), (24, -34, 4), (30, 2, 3)]:
            lucky += ink.sparkle(lx + dx * 1.3, H - 78 + dy * 1.3, r + 1, lrnd, fill=ink_c, dur=lrnd.uniform(1.8, 2.8))
        meadow += f'<g class="bob">{lucky}</g>'
    defs = (f'<linearGradient id="f" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
            f'<stop offset=".12" stop-color="#fff"/><stop offset=".88" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
            f'<mask id="m"><rect width="{W}" height="{H}" fill="url(#f)"/></mask>')
    body = "".join(p) + f'<g mask="url(#m)">{meadow}</g>'
    return _svg(W, H, body, "daily clover luck", defs)


# ------------------------------------------------------------------ stats card
def stats_card(st):
    W, H = 600, 300
    rnd = random.Random(11)
    p = []
    t, _ = write("github, in clovers", 40, 62, 22, rnd, font="scripts", width=2.2, skew=0)
    p.append(t)
    rows = [("stars", st["stars"]), ("commits", st["commits"]), ("pull requests", st["prs"]), ("issues", st["issues"])]
    for i, (label, val) in enumerate(rows):
        y = 118 + i * 42
        bullet = ink.ink_clover(52, y - 8, 6, 3, rnd, sw=1.1, angle=rnd.uniform(0, 60), solid=i % 2 == 1)
        lt, _ = write(label, 70, y, 15, rnd, width=1.6)
        vt, _ = write(_short(val), 300, y, 17, rnd, width=2.0, anchor="end")
        p += [bullet, lt, vt]
    # rank clover: leaves fill up as the rank grows
    cx, cy = 450, 150
    filled = 4 * (1 - st["percentile"] / 100)
    stem = ink.line_pts((cx - 2, cy + 6), (cx - 18, cy + 112), rnd, .6, 20, 12)
    p.append(f'<path d="{ink.d(stem, False)}" fill="none" stroke="{INK}" stroke-width="1.6" stroke-linecap="round"/>')
    p.append(ink.glow(cx, cy, rnd, rx=72, ry=64, ticks=False))
    p.append(ink.watercolour_clover(cx, cy, 52, 4, rnd, "rk", fill_leaves=filled, sw=1.6))
    rt, _ = write(st["level"], 530, 262, 26, rnd, width=2.6, anchor="end")
    pt, _ = write(f"top {st['percentile']:.0f}%", 530, 284, 11, rnd, width=1.2, anchor="end")
    p += [rt, f'<g opacity=".6">{pt}</g>']
    return _svg(W, H, _paper_card(W, H, "".join(p)), "GitHub stats")


def _short(n):
    return f"{n / 1000:.1f}k".replace(".0k", "k") if n >= 1000 else str(n)


# ------------------------------------------------------------------ languages clover
def langs_card(waka):
    W, H = 600, 300
    rnd = random.Random(12)
    p = []
    t, _ = write("what i wrote, last 30 days", 40, 62, 22, rnd, font="scripts", width=2.2, skew=0)
    p.append(t)
    langs = [(l["name"], l["percent"]) for l in waka["languages"] if l["percent"] >= 1][:4]
    if len(waka["languages"]) > 4:
        rest = 100 - sum(v for _, v in langs[:3])
        langs = langs[:3] + [("other", rest)]
    langs = langs or [("nothing yet", 100)]
    top = max(v for _, v in langs)
    kinds = ["wash", "hatch", "dots", "empty"]
    styles = [(kinds[i], .5 + .5 * math.sqrt(v / top)) for i, (_, v) in enumerate(langs)]
    cx, cy = 150, 172
    stem = ink.line_pts((cx, cy + 6), (cx - 14, cy + 120), rnd, .6, 20, 10)
    p.append(f'<path d="{ink.d(stem, False)}" fill="none" stroke="{INK}" stroke-width="1.6" stroke-linecap="round"/>')
    p.append(ink.watercolour_clover(cx, cy, 64, len(langs), rnd, "lg", styles=styles, angle=0 if len(langs) == 4 else 20, sw=1.6))
    for i, (name, v) in enumerate(langs):
        y = 116 + i * 40
        sw = ink.watercolour_clover(298, y - 4, 17, 1, random.Random(i), f"sw{i}", styles=[(kinds[i], 1)], angle=40, sw=1.2)
        nt, _ = write(name.lower(), 322, y, 15, rnd, width=1.6)
        vt, _ = write(f"{v:.0f}%", 560, y, 15, rnd, width=1.6, anchor="end")
        p += [sw, nt, vt]
    tt, _ = write(waka["total"], 560, 272, 12, rnd, width=1.3, anchor="end")
    p.append(f'<g opacity=".6">{tt}</g>')
    return _svg(W, H, _paper_card(W, H, "".join(p)), "Languages, last 30 days")
