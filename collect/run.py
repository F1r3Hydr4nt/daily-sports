"""Fetch every source, merge, and write fixtures.json.  Usage: python3 -m collect.run fixtures.json
Blocked or failed sources are recorded under "skipped" and never invented."""
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from . import covers, espn, footballontv, predicd
from .football import merge

DUB = ZoneInfo("Europe/Dublin")
UA = "Mozilla/5.0"
ESPN = "https://www.espn.com"


def curl(url: str):
    r = subprocess.run(["curl", "-s", "-m", "40", "-A", UA, "-w", "\n%{http_code}", url], capture_output=True, text=True)
    body, _, code = r.stdout.rpartition("\n")
    return (int(code) if code.isdigit() else 0), body


def get(url: str, skipped: list, fetcher=curl):
    code, body = fetcher(url)
    if code != 200 or not body:
        skipped.append(f"{url}: HTTP {code or 'no response'}, not used")
        return None
    return body


def attach_covers(games: list, picks_by_sport: dict, fetched_at) -> list:
    notes = []
    for sport, picks in picks_by_sport.items():
        pub = covers.published(picks)
        if picks and not pub:
            notes.append(f"covers.com/picks/{sport}: Odds Shark predicted scores show 0.00 (not published yet), no model")
        for g in games:
            if g["sport"] != sport:
                continue
            for p in pub:
                if covers.same_team(p["away"], g["away"]) and covers.same_team(p["home"], g["home"]):
                    g["models"].append({"name": "Odds Shark computer pick", "kind": "statistical-model",
                                        "source": "covers.com", "url": f"https://www.covers.com/picks/{sport}",
                                        "fetched_at": fetched_at, "score": {"home": p["home_score"], "away": p["away_score"]}})
                    break
    return notes


def collect(now: datetime) -> dict:
    now = now.astimezone(DUB)
    utc_now = now.astimezone(timezone.utc)
    window = (utc_now, utc_now + timedelta(hours=24))
    days = [(now + timedelta(days=d)).strftime("%Y%m%d") for d in (0, 1)]
    skipped, fixtures = [], []

    fotv = get("https://www.live-footballontv.com/", skipped)
    pred = get(predicd.URL, skipped)
    listings = footballontv.parse(fotv) if fotv else []
    preds = predicd.parse(pred, now.year) if pred else []
    fixtures += merge(listings, preds, now, fetched_at=utc_now)

    us = []
    for path, (sport, label) in espn.TEAM_LEAGUES.items():
        url = f"{ESPN}/{path}/schedule/_/date/{days[0]}"
        page = get(url, skipped)
        content = espn.extract(page) if page else None
        if content:
            us += espn.team_events(content, sport, label, url, window)
    picks = {}
    for league in ("nfl", "mlb", "nhl", "wnba"):
        page = get(f"https://www.covers.com/picks/{league}", skipped)
        if page:
            picks[league] = covers.parse(page)
    skipped += attach_covers(us, picks, utc_now)
    fixtures += us

    for d in days:
        for name, fn, path in (("tennis", espn.tennis, f"tennis/scoreboard/_/date/{d}"),
                               ("rugby", espn.rugby, f"rugby/scoreboard/_/date/{d}")):
            url = f"{ESPN}/{path}"
            page = get(url, skipped)
            content = espn.extract(page) if page else None
            if content:
                fixtures += fn(content, url, window)
    for name, fn, path in (("mma", espn.mma, "mma/schedule"), ("golf", espn.golf, "golf/schedule")):
        url = f"{ESPN}/{path}"
        page = get(url, skipped)
        content = espn.extract(page) if page else None
        if content:
            fixtures += fn(content, url, window)

    for src in ("cricket (ESPN/Cricinfo)", "darts", "snooker", "boxing", "GAA", "horse and greyhound racing", "esports"):
        skipped.append(f"{src}: no collector yet, not covered in this run")
    return {"generated_at": now.isoformat(), "skipped": skipped, "fixtures": fixtures}


def _json(o):
    if isinstance(o, datetime):
        return o.astimezone(timezone.utc).isoformat()
    raise TypeError(type(o))


if __name__ == "__main__":
    data = collect(datetime.now(DUB))
    with open(sys.argv[1], "w") as f:
        json.dump(data, f, indent=1, default=_json)
    print(f"{len(data['fixtures'])} fixtures, {len(data['skipped'])} skipped notes")
