"""Daily build of the profile pictures.

    python scripts/clover/build.py                 # fetch data, draw everything into assets/
    python scripts/clover/build.py --offline       # use cache.json only (no network)
    python scripts/clover/build.py --date 2027-01-05 --offline   # preview another day/season

Env: GH_TOKEN (GitHub token with read:user), WAKATIME_API_KEY. Missing or failing APIs fall back to cache.json.
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
import scenes  # noqa: E402
from ink import season_of  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ASSETS = os.path.join(ROOT, "assets")
CACHE = os.path.join(HERE, "cache.json")
LOGIN = "er-Bilim"
LUCK_START = dt.date(2026, 11, 13)
LUCK_ODDS = 10  # one day in ten
BISHKEK = dt.timezone(dt.timedelta(hours=6))


# ------------------------------------------------------------------ data
def _get(url, headers, body=None):
    req = urllib.request.Request(url, data=body, headers={"User-Agent": "clover-build", **headers})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_github(token):
    h = {"Authorization": f"bearer {token}"}
    q = """query($login: String!) { user(login: $login) {
      followers { totalCount }
      pullRequests { totalCount }
      issues { totalCount }
      contributionsCollection { totalPullRequestReviewContributions totalCommitContributions }
      repositories(first: 100, ownerAffiliations: [OWNER, ORGANIZATION_MEMBER], isFork: false,
                   orderBy: {field: STARGAZERS, direction: DESC}) { nodes { stargazerCount } } } }"""
    u = _get("https://api.github.com/graphql", h, json.dumps({"query": q, "variables": {"login": LOGIN}}).encode())["data"]["user"]
    try:  # all-time commits, like include_all_commits=true
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
    return {**raw, **rank(raw)}


def rank(s):
    """Same formula as github-readme-stats (all commits mode), so the letter stays familiar."""
    exp_cdf = lambda x: 1 - 2 ** -x  # noqa: E731
    log_cdf = lambda x: x / (1 + x)  # noqa: E731
    parts = [(2, exp_cdf(s["commits"] / 1000)), (3, exp_cdf(s["prs"] / 50)), (1, exp_cdf(s["issues"] / 25)),
             (1, exp_cdf(s["reviews"] / 2)), (4, log_cdf(s["stars"] / 50)), (1, log_cdf(s["followers"] / 10))]
    r = 1 - sum(w * v for w, v in parts) / sum(w for w, _ in parts)
    thresholds = [1, 12.5, 25, 37.5, 50, 62.5, 75, 87.5, 100]
    levels = ["S", "A+", "A", "A-", "B+", "B", "B-", "C+", "C"]
    level = next(l for t, l in zip(thresholds, levels) if r * 100 <= t)
    return {"level": level, "percentile": round(r * 100, 1)}


def fetch_waka(key):
    auth = base64.b64encode(key.encode()).decode()
    data = _get("https://wakatime.com/api/v1/users/current/stats/last_30_days", {"Authorization": f"Basic {auth}"})["data"]
    langs = [{"name": l["name"], "percent": l["percent"]} for l in data.get("languages", []) if l["name"] != "Other"]
    if not langs:
        raise ValueError("wakatime stats not ready yet")
    return {"languages": langs, "total": data.get("human_readable_total", "")}


# ------------------------------------------------------------------ luck
def lucky(day):
    return int(hashlib.sha256(f"clover:{day.isoformat()}".encode()).hexdigest(), 16) % LUCK_ODDS == 0


def found_until(day):
    n, d = 0, LUCK_START
    while d <= day:
        n += lucky(d)
        d += dt.timedelta(days=1)
    return n


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--date")
    a = ap.parse_args()

    cache = json.load(open(CACHE))
    if not a.offline:
        for key, env, fn in [("stats", "GH_TOKEN", fetch_github), ("waka", "WAKATIME_API_KEY", fetch_waka)]:
            if os.environ.get(env):
                try:
                    cache[key] = fn(os.environ[env])
                except Exception as e:  # keep yesterday's numbers rather than failing the whole build
                    print(f"[{key}] using cache: {e}")
        json.dump(cache, open(CACHE, "w"), indent=2)

    today = dt.date.fromisoformat(a.date) if a.date else dt.datetime.now(BISHKEK).date()
    season = season_of(today.month)
    out = {
        "header.svg": scenes.header(season),
        "stats.svg": scenes.stats_card(cache["stats"]),
        "langs.svg": scenes.langs_card(cache["waka"]),
    }
    for mode in ("dark", "light"):
        out[f"footer-{mode}.svg"] = scenes.footer(mode, lucky(today), found_until(today), season)
    os.makedirs(ASSETS, exist_ok=True)
    for name, svg in out.items():
        with open(os.path.join(ASSETS, name), "w", encoding="utf-8", newline="\n") as f:
            f.write(svg)
    print(f"{today} {season} lucky={lucky(today)} found={found_until(today)} -> {', '.join(out)}")


if __name__ == "__main__":
    main()
