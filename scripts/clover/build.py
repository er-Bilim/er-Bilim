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


def fetch_rhythm(token):
    """Commit hours (Bishkek time) from recent public commits + contribution streaks from the calendar."""
    h = {"Authorization": f"bearer {token}", "Accept": "application/vnd.github+json"}
    hours = [0] * 24
    for page in (1, 2, 3):
        items = _get(f"https://api.github.com/search/commits?q=author:{LOGIN}&sort=author-date&order=desc&per_page=100&page={page}", h)["items"]
        for it in items:
            t = dt.datetime.fromisoformat(it["commit"]["author"]["date"].replace("Z", "+00:00")).astimezone(BISHKEK)
            hours[t.hour] += 1
        if len(items) < 100:
            break
    q = """query($login: String!) { user(login: $login) { contributionsCollection { contributionCalendar { weeks { contributionDays { date contributionCount } } } } } }"""
    cal = _get("https://api.github.com/graphql", {"Authorization": f"bearer {token}"},
               json.dumps({"query": q, "variables": {"login": LOGIN}}).encode())["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    best = run = 0
    for d in days:
        run = run + 1 if d["contributionCount"] else 0
        best = max(best, run)
    cur = 0
    for i, d in enumerate(reversed(days)):
        if d["contributionCount"]:
            cur += 1
        elif i == 0:
            continue  # today without commits yet doesn't break the streak
        else:
            break
    return {"hours": hours, "streak": cur, "best_streak": best}


def fetch_repos(token):
    """Latest public repos with language, size and commit count."""
    q = """query($login: String!) { user(login: $login) { repositories(first: 8, privacy: PUBLIC, ownerAffiliations: [OWNER], isFork: false,
      orderBy: {field: PUSHED_AT, direction: DESC}) { nodes { name diskUsage stargazerCount primaryLanguage { name }
      defaultBranchRef { target { ... on Commit { history { totalCount } } } } } } } }"""
    nodes = _get("https://api.github.com/graphql", {"Authorization": f"bearer {token}"},
                 json.dumps({"query": q, "variables": {"login": LOGIN}}).encode())["data"]["user"]["repositories"]["nodes"]
    out = []
    for n in nodes:
        if n["name"].lower() == LOGIN.lower():
            continue
        commits = ((n.get("defaultBranchRef") or {}).get("target") or {}).get("history", {}).get("totalCount", 0)
        out.append({"name": n["name"], "lang": (n.get("primaryLanguage") or {}).get("name"), "size": n.get("diskUsage") or 0,
                    "stars": n["stargazerCount"], "commits": commits})
    return out[:4]


def fetch_calendar(token):
    """Last year of contributions (same data as the green grid on the profile) + streaks."""
    q = """query($login: String!) { user(login: $login) { contributionsCollection { contributionCalendar {
      totalContributions weeks { contributionDays { date contributionCount } } } } } }"""
    cal = _get("https://api.github.com/graphql", {"Authorization": f"bearer {token}"},
               json.dumps({"query": q, "variables": {"login": LOGIN}}).encode())["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = [(d["date"], d["contributionCount"]) for w in cal["weeks"] for d in w["contributionDays"]]
    streak = 0
    for i, (_, c) in enumerate(reversed(days)):
        if c:
            streak += 1
        elif i:          # today may still be empty — the streak is not broken yet
            break
    longest = run = 0
    for _, c in days:
        run = run + 1 if c else 0
        longest = max(longest, run)
    return {"days": days, "total": cal["totalContributions"], "streak": streak, "longest": longest}


def fetch_commits(token):
    """Newest own commits across public repos (for the train). Messages only, no diffs."""
    h = {"Authorization": f"bearer {token}"}
    uid = _get("https://api.github.com/graphql", h, json.dumps({"query": "query($l: String!) { user(login: $l) { id } }",
                                                                "variables": {"l": LOGIN}}).encode())["data"]["user"]["id"]
    q = """query($login: String!, $id: ID!) { user(login: $login) { repositories(first: 6, privacy: PUBLIC, ownerAffiliations: [OWNER],
      isFork: false, orderBy: {field: PUSHED_AT, direction: DESC}) { nodes { name primaryLanguage { name }
      defaultBranchRef { target { ... on Commit { history(first: 4, author: {id: $id}) { nodes { oid messageHeadline committedDate } } } } } } } } }"""
    nodes = _get("https://api.github.com/graphql", h, json.dumps({"query": q, "variables": {"login": LOGIN, "id": uid}}).encode()
                 )["data"]["user"]["repositories"]["nodes"]
    out = []
    for n in nodes:
        if n["name"].lower() == LOGIN.lower():
            continue
        hist = (((n.get("defaultBranchRef") or {}).get("target") or {}).get("history") or {}).get("nodes", [])
        for c in hist:
            out.append({"repo": n["name"], "lang": (n.get("primaryLanguage") or {}).get("name"), "msg": c["messageHeadline"],
                        "date": c["committedDate"], "oid": c["oid"]})
    return sorted(out, key=lambda c: c["date"], reverse=True)[:4]


def fetch_langs(token):
    """Bytes of code per language across all own repos, private ones included (the token must see them)."""
    h = {"Authorization": f"bearer {token}"}
    q = """query($after: String) { viewer { repositories(first: 100, after: $after, ownerAffiliations: [OWNER], isFork: false) {
      pageInfo { hasNextPage endCursor }
      nodes { name isPrivate languages(first: 20, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name color } } } } } } }"""
    langs, repos, private, after = {}, 0, 0, None
    while True:
        r = _get("https://api.github.com/graphql", h, json.dumps({"query": q, "variables": {"after": after}}).encode()
                 )["data"]["viewer"]["repositories"]
        for n in r["nodes"]:
            repos += 1
            private += n["isPrivate"]
            for e in n["languages"]["edges"]:
                L = langs.setdefault(e["node"]["name"], {"name": e["node"]["name"], "bytes": 0, "color": e["node"]["color"], "repos": 0})
                L["bytes"] += e["size"]
                L["repos"] += 1
        if not r["pageInfo"]["hasNextPage"]:
            break
        after = r["pageInfo"]["endCursor"]
    return {"langs": sorted(langs.values(), key=lambda x: -x["bytes"]), "repos": repos, "private": private}


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
    """Languages over the longest range WakaTime still allows for this account.

    Since late Oct 2026 the API answers 403 to /stats/last_30_days for many (free) accounts,
    so every source is tried in turn and the first one that works wins."""
    auth = {"Authorization": "Basic " + base64.b64encode(key.encode()).decode()}
    base = "https://wakatime.com/api/v1/users/current"

    def from_stats(rng):
        data = _get(f"{base}/stats/{rng}", auth)["data"]
        langs = [{"name": l["name"], "percent": l["percent"], "hours": round(l.get("total_seconds", 0) / 3600, 1)}
                 for l in data.get("languages", []) if l["name"] != "Other"]
        return langs, data.get("human_readable_total", "")

    def from_summaries(rng):
        days = _get(f"{base}/summaries?range={rng.replace('_', ' ').title()}", auth)["data"]
        secs = {}
        for day in days:
            for l in day.get("languages", []):
                secs[l["name"]] = secs.get(l["name"], 0) + l.get("total_seconds", 0)
        total = sum(secs.values())
        langs = [{"name": n, "percent": round(100 * s / total, 2), "hours": round(s / 3600, 1)}
                 for n, s in sorted(secs.items(), key=lambda kv: -kv[1]) if n != "Other" and total]
        h, m = divmod(int(total // 60), 60)
        return langs, f"{h} hrs {m} mins"

    tries = [("last 30 days", lambda: from_stats("last_30_days")), ("last 7 days", lambda: from_stats("last_7_days")),
             ("last 7 days", lambda: from_summaries("last_7_days"))]
    for label, fn in tries:
        try:
            langs, total = fn()
            if langs:
                print(f"[waka] ok: {label}")
                return {"languages": langs, "total": total, "range": label}
            print(f"[waka] {label}: empty")
        except Exception as e:
            print(f"[waka] {label}: {_explain(e)}")
    raise ValueError("every WakaTime source failed")


WAKA_BADGE = "https://wakatime.com/badge/user/4cb5727d-c163-4c42-866c-a48cd6d37d56.svg"


def fetch_all_time_badge():
    """The public WakaTime badge carries the all-time total, no API key needed."""
    import re
    req = urllib.request.Request(WAKA_BADGE, headers={"User-Agent": "clover-build"})
    with urllib.request.urlopen(req, timeout=30) as r:
        svg = r.read().decode()
    m = re.search(r"([\d,]+ hrs?(?: \d+ mins?)?)", svg)
    if not m:
        raise ValueError("no time in badge")
    return m.group(1)


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
                cache["repos"] = fetch_repos(os.environ["GH_TOKEN"])
                cache["calendar"] = fetch_calendar(os.environ["GH_TOKEN"])
                cache["commits"] = fetch_commits(os.environ["GH_TOKEN"])
                cache["langs_gh"] = fetch_langs(os.environ["GH_TOKEN"])
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
        try:  # all-time total from the public badge works even without the API key
            cache["waka"]["all_time"] = fetch_all_time_badge()
        except Exception as e:
            print(f"[waka] badge: {_explain(e)}")
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
    st["repos"] = cache.get("repos", [])
    st["calendar"] = cache.get("calendar", {})
    st["commits"] = cache.get("commits", [])
    st["langs_gh"] = cache.get("langs_gh", {})
    out = {
        "header.svg": world.header(st),
        "stats.svg": world.stats_card(st),
        "repos.svg": world.archipelago_card(st), "land.svg": world.terrain_card(st), "train.svg": world.train_card(st), "chest.svg": world.chest_card(st), "langs.svg": world.strata_card(st),
        "footer.svg": world.garden_footer(st),
        "divider.svg": world.divider(),
        "time.svg": world.time_card(st),
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
