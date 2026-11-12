"""Builds the profile pictures (the floating island + cards).

    python scripts/clover/build.py                         # fetch data, draw into assets/
    python scripts/clover/build.py --offline               # cache.json only
    python scripts/clover/build.py --offline --date 2027-01-01 --phase night --weekly 0   # preview a situation

Env: GH_TOKEN (read:user), WAKATIME_API_KEY. Failing APIs fall back to cache.json.
Needs: fonttools.
"""
import argparse
import base64
import datetime as dt
import hashlib
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import world  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ASSETS = os.path.join(ROOT, "assets")
CACHE = os.path.join(HERE, "cache.json")
LOGIN = "er-Bilim"
LUCK_START = dt.date(2026, 11, 13)
LUCK_ODDS = 10
BISHKEK = dt.timezone(dt.timedelta(hours=6))
LINKS = [("telegram", "erk_bilim"), ("linkedin", "bilim-erkinbekov"), ("instagram", "esoatna")]


def _get(url, headers, body=None):
    req = urllib.request.Request(url, data=body, headers={"User-Agent": "clover-build", **headers})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_github(token):
    h = {"Authorization": f"bearer {token}"}
    week_ago = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    q = """query($login: String!, $from: DateTime!) { user(login: $login) {
      followers { totalCount }
      pullRequests { totalCount }
      issues { totalCount }
      contributionsCollection { totalPullRequestReviewContributions totalCommitContributions }
      week: contributionsCollection(from: $from) { totalCommitContributions }
      repositories(first: 100, ownerAffiliations: [OWNER, ORGANIZATION_MEMBER], isFork: false,
                   orderBy: {field: STARGAZERS, direction: DESC}) { nodes { stargazerCount } }
      recent: repositories(first: 5, privacy: PUBLIC, ownerAffiliations: [OWNER], orderBy: {field: PUSHED_AT, direction: DESC}) { nodes { name } } } }"""
    u = _get("https://api.github.com/graphql", h,
             json.dumps({"query": q, "variables": {"login": LOGIN, "from": week_ago}}).encode())["data"]["user"]
    try:
        commits = _get(f"https://api.github.com/search/commits?q=author:{LOGIN}&per_page=1",
                       {**h, "Accept": "application/vnd.github+json"})["total_count"]
    except Exception:
        commits = u["contributionsCollection"]["totalCommitContributions"]
    raw = {
        "commits": commits,
        "prs": u["pullRequests"]["totalCount"],
        "issues": u["issues"]["totalCount"],
        "reviews": u["contributionsCollection"]["totalPullRequestReviewContributions"],
        "stars": sum(n["stargazerCount"] for n in u["repositories"]["nodes"]),
        "followers": u["followers"]["totalCount"],
    }
    # only public repos, never the profile repo itself (client/private work stays private)
    repo = next((n["name"] for n in u["recent"]["nodes"] if n["name"].lower() != LOGIN.lower()), "")
    return {**raw, **rank(raw)}, u["week"]["totalCommitContributions"], repo


def rank(s):
    """Same formula as github-readme-stats (all commits mode)."""
    exp_cdf = lambda x: 1 - 2 ** -x  # noqa: E731
    log_cdf = lambda x: x / (1 + x)  # noqa: E731
    parts = [(2, exp_cdf(s["commits"] / 1000)), (3, exp_cdf(s["prs"] / 50)), (1, exp_cdf(s["issues"] / 25)),
             (1, exp_cdf(s["reviews"] / 2)), (4, log_cdf(s["stars"] / 50)), (1, log_cdf(s["followers"] / 10))]
    r = 1 - sum(w * v for w, v in parts) / sum(w for w, _ in parts)
    thresholds = [1, 12.5, 25, 37.5, 50, 62.5, 75, 87.5, 100]
    levels = ["S", "A+", "A", "A-", "B+", "B", "B-", "C+", "C"]
    return {"level": next(l for t, l in zip(thresholds, levels) if r * 100 <= t), "percentile": round(r * 100, 1)}


def fetch_waka(key):
    """Languages for the last 30 days (falls back to 7 days) + all-time total coding time."""
    auth = {"Authorization": "Basic " + base64.b64encode(key.encode()).decode()}
    out = {}
    for rng in ("last_30_days", "last_7_days"):
        data = _get(f"https://wakatime.com/api/v1/users/current/stats/{rng}", auth)["data"]
        langs = [{"name": l["name"], "percent": l["percent"], "hours": round(l.get("total_seconds", 0) / 3600, 1)}
                 for l in data.get("languages", []) if l["name"] != "Other"]
        if langs:
            out = {"languages": langs, "total": data.get("human_readable_total", ""), "range": rng}
            break
        print(f"[waka] {rng}: no languages yet (is_up_to_date={data.get('is_up_to_date')}, status={data.get('status')})")
    try:
        at = _get("https://wakatime.com/api/v1/users/current/all_time_since_today", auth)["data"]
        out["all_time"] = at.get("text", "")
    except Exception as e:
        print(f"[waka] all-time: {e}")
    if not out.get("languages"):
        raise ValueError("wakatime returned no languages")
    return out


def _explain(e):
    """Show the HTTP status and body, so a failing secret/endpoint is visible in the Action log."""
    body = ""
    if hasattr(e, "read"):
        try:
            body = e.read().decode()[:200]
        except Exception:
            pass
    return f"{e} {body}".strip()


def lucky(day):
    return int(hashlib.sha256(f"clover:{day.isoformat()}".encode()).hexdigest(), 16) % LUCK_ODDS == 0


def found_until(day):
    n, d = 0, LUCK_START
    while d <= day:
        n += lucky(d)
        d += dt.timedelta(days=1)
    return n


def phase_of(hour):
    if 6 <= hour < 11:
        return "morning"
    if 11 <= hour < 18:
        return "day"
    if 18 <= hour < 22:
        return "evening"
    return "night"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--date")
    ap.add_argument("--phase", choices=["morning", "day", "evening", "night"])
    ap.add_argument("--weekly", type=int)
    ap.add_argument("--found", type=int)
    ap.add_argument("--lucky", action="store_true")
    ap.add_argument("--commits", type=int)
    ap.add_argument("--out", default=ASSETS)
    a = ap.parse_args()

    cache = json.load(open(CACHE))
    if not a.offline:
        if os.environ.get("GH_TOKEN"):
            try:
                cache["stats"], cache["weekly"], cache["repo"] = fetch_github(os.environ["GH_TOKEN"])
            except Exception as e:  # keep yesterday's numbers instead of failing
                print(f"[github] using cache: {_explain(e)}")
        if os.environ.get("WAKATIME_API_KEY"):
            try:
                fresh = fetch_waka(os.environ["WAKATIME_API_KEY"])
                fresh.setdefault("all_time", cache.get("waka", {}).get("all_time", ""))
                cache["waka"] = fresh
            except Exception as e:
                print(f"[waka] using cache: {_explain(e)}")
        else:
            print("[waka] WAKATIME_API_KEY is not set, using cache")
        json.dump(cache, open(CACHE, "w"), indent=2)

    now = dt.datetime.now(BISHKEK)
    today = dt.date.fromisoformat(a.date) if a.date else now.date()
    phase = a.phase or phase_of(now.hour)
    stats = dict(cache["stats"])
    if a.commits is not None:
        stats["commits"] = a.commits
    is_lucky = a.lucky or lucky(today)
    found = a.found if a.found is not None else found_until(today)
    st = world.make_state(today, phase, world_season(today.month), stats, cache["waka"],
                          a.weekly if a.weekly is not None else cache.get("weekly", 0), cache.get("repo", ""), is_lucky, found)
    out = {
        "header.svg": world.header(st),
        "stats.svg": world.stats_card(st),
        "langs.svg": world.districts_card(st),
        "footer.svg": world.garden_footer(st),
        "divider.svg": world.divider(),
    }
    for kind, handle in LINKS:
        out[f"link-{kind}.svg"] = world.link_button(kind, handle, st)
    os.makedirs(a.out, exist_ok=True)
    for name, svg in out.items():
        with open(os.path.join(a.out, name), "w", encoding="utf-8", newline="\n") as f:
            f.write(svg)
    print(f"{today} {phase} {st['season']} weather={st['weather']} lucky={is_lucky} found={found} "
          f"level={st['level']} holiday={st['holiday']} rare={sorted(st['rare'])}")


def world_season(month):
    return {12: "winter", 1: "winter", 2: "winter", 3: "spring", 4: "spring", 5: "spring",
            6: "summer", 7: "summer", 8: "summer"}.get(month, "autumn")


if __name__ == "__main__":
    main()
