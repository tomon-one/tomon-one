#!/usr/bin/env python3
"""Монохромные карточки для профиля (подписи на английском): статистика, языки, активность за 30 дней.

Запуск: GITHUB_TOKEN=… python3 scripts/cards.py <login> <папка>
Рисует <name>-dark.svg и <name>-light.svg.
"""
import datetime as dt
import json
import os
import sys
import urllib.request
from collections import Counter
from xml.sax.saxutils import escape

LOGIN = sys.argv[1] if len(sys.argv) > 1 else "tomon-one"
OUT = sys.argv[2] if len(sys.argv) > 2 else "cards"

THEMES = {
    "dark": dict(bg="#0d1117", border="#30363d", fg="#f0f6fc", muted="#9198a1", faint="#21262d"),
    "light": dict(bg="#ffffff", border="#d1d9e0", fg="#1f2328", muted="#59636e", faint="#eff2f5"),
}
FONT = "font-family:'Segoe UI',Ubuntu,'Noto Sans',Helvetica,Arial,sans-serif"
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()

QUERY = """
query($login: String!, $merged: String!) {
  user(login: $login) {
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100, privacy: PUBLIC) {
      nodes {
        name
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
  prs: search(query: $merged, type: ISSUE) { issueCount }
}
"""


def repos(d):
    # репозиторий профиля (<login>/<login>) — не проект
    return [r for r in d["user"]["repositories"]["nodes"] if r["name"].lower() != LOGIN.lower()]


def fetch():
    body = json.dumps({"query": QUERY, "variables": {
        "login": LOGIN, "merged": f"author:{LOGIN} is:pr is:merged"}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", body, {
        "Authorization": f"bearer {os.environ['GITHUB_TOKEN']}",
        "Content-Type": "application/json", "User-Agent": LOGIN})
    data = json.load(urllib.request.urlopen(req, timeout=30))
    if "errors" in data:
        sys.exit(f"GraphQL: {data['errors']}")
    return data["data"]


def streaks(days):
    counts = [d["contributionCount"] for d in days]
    longest = cur = 0
    for c in counts:
        cur = cur + 1 if c else 0
        longest = max(longest, cur)
    # текущая серия: сегодняшний пустой день ещё не обрывает её
    i = len(counts) - 1
    if counts and counts[i] == 0:
        i -= 1
    current = 0
    while i >= 0 and counts[i]:
        current += 1
        i -= 1
    return current, longest


def ndays(n):
    return f"{n} day" if n == 1 else f"{n} days"


def frame(t, w, h, title, inner):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="6" fill="{t["bg"]}" stroke="{t["border"]}"/>'
            f'<text x="24" y="36" fill="{t["fg"]}" style="{FONT};font-size:16px;font-weight:600">{escape(title)}</text>'
            f'{inner}</svg>')


def stats_card(t, d):
    u = d["user"]
    cc = u["contributionsCollection"]
    days = [x for w in cc["contributionCalendar"]["weeks"] for x in w["contributionDays"]]
    current, longest = streaks(days)
    stars = sum(r["stargazerCount"] for r in repos(d))
    count = len(repos(d))
    rows = [
        ("Contributions this year", cc["contributionCalendar"]["totalContributions"]),
        ("Commits", cc["totalCommitContributions"] + cc["restrictedContributionsCount"]),
        ("Merged PRs", d["prs"]["issueCount"]),
        ("Stars", stars) if stars else ("Projects", count),
        ("Current streak", ndays(current)),
        ("Longest streak", ndays(longest)),
    ]
    inner = ""
    for i, (k, v) in enumerate(rows):
        y = 70 + i * 24
        inner += (f'<text x="24" y="{y}" fill="{t["muted"]}" style="{FONT};font-size:14px">{k}</text>'
                  f'<text x="316" y="{y}" text-anchor="end" fill="{t["fg"]}" '
                  f'style="{FONT};font-size:14px;font-weight:600">{v}</text>')
    return frame(t, 340, 70 + len(rows) * 24 - 4, "Stats", inner)


def langs_card(t, d):
    sizes = Counter()
    for r in repos(d):
        for e in r["languages"]["edges"]:
            sizes[e["node"]["name"]] += e["size"]
    total = sum(sizes.values()) or 1
    inner = ""
    for i, (name, s) in enumerate(sizes.most_common(6)):
        y = 70 + i * 24
        share = s / total
        inner += (f'<text x="24" y="{y}" fill="{t["muted"]}" style="{FONT};font-size:14px">{escape(name)}</text>'
                  f'<rect x="124" y="{y-9}" width="140" height="8" rx="4" fill="{t["faint"]}"/>'
                  f'<rect x="124" y="{y-9}" width="{max(140 * share, 8):.1f}" height="8" rx="4" fill="{t["fg"]}"/>'
                  f'<text x="316" y="{y}" text-anchor="end" fill="{t["fg"]}" '
                  f'style="{FONT};font-size:14px;font-weight:600">{100 * share:.0f}%</text>')
    return frame(t, 340, 210, "Languages", inner)


def activity_card(t, d):
    days = [x for w in d["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
            for x in w["contributionDays"]][-30:]
    counts = [x["contributionCount"] for x in days]
    W, H, L, R, T, B = 700, 220, 44, 20, 56, 36
    pw, ph = W - L - R, H - T - B
    top = max(max(counts), 1)
    step = pw / (len(counts) - 1)
    pts = [(L + i * step, T + ph - ph * c / top) for i, c in enumerate(counts)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"{L},{T+ph} {line} {L+pw},{T+ph}"
    grid = ""
    for k in range(5):
        y = T + ph * k / 4
        v = round(top * (4 - k) / 4)
        grid += (f'<line x1="{L}" y1="{y:.1f}" x2="{L+pw}" y2="{y:.1f}" stroke="{t["faint"]}"/>'
                 f'<text x="{L-8}" y="{y+4:.1f}" text-anchor="end" fill="{t["muted"]}" '
                 f'style="{FONT};font-size:11px">{v}</text>')
    labels = ""
    for i in range(0, len(days), 5):
        date = dt.date.fromisoformat(days[i]["date"])
        labels += (f'<text x="{pts[i][0]:.1f}" y="{H-12}" text-anchor="middle" fill="{t["muted"]}" '
                   f'style="{FONT};font-size:11px">{MONTHS[date.month-1]} {date.day}</text>')
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.5" fill="{t["fg"]}"/>'
                   for (x, y), c in zip(pts, counts) if c)
    inner = (f'<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
             f'<stop offset="0" stop-color="{t["fg"]}" stop-opacity=".22"/>'
             f'<stop offset="1" stop-color="{t["fg"]}" stop-opacity="0"/></linearGradient></defs>'
             f'{grid}<polygon points="{area}" fill="url(#g)"/>'
             f'<polyline points="{line}" fill="none" stroke="{t["fg"]}" stroke-width="2" '
             f'stroke-linejoin="round"/>{dots}{labels}')
    return frame(t, W, H, "Activity, last 30 days", inner)


def main():
    d = fetch()
    os.makedirs(OUT, exist_ok=True)
    for name, fn in [("stats", stats_card), ("langs", langs_card), ("activity", activity_card)]:
        for theme, t in THEMES.items():
            with open(os.path.join(OUT, f"{name}-{theme}.svg"), "w") as f:
                f.write(fn(t, d))


if __name__ == "__main__":
    main()
