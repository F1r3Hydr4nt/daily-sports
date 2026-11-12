"""Fetch every source, merge, and write fixtures.json.  Usage: python3 -m collect.run fixtures.json
Blocked or failed sources are recorded under "skipped" and never invented."""
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from . import covers, espn, flashscore, footballontv, predicd, setprob
from .football import align, merge, one_team_match, teams_match

DUB = ZoneInfo("Europe/Dublin")
UA = "Mozilla/5.0"
ESPN = "https://www.espn.com"


def curl(url: str, headers: dict = None, follow: bool = False):
    hs = [a for k, v in (headers or {}).items() for a in ("-H", f"{k}: {v}")]
    r = subprocess.run(["curl", "-s", "-m", "40", "-A", UA, *(["-L"] if follow else []), *hs, "-w", "\n%{http_code}", url], capture_output=True, text=True)
    body, _, code = r.stdout.rpartition("\n")
    return (int(code) if code.isdigit() else 0), body


def get(url: str, skipped: list, fetcher=curl):
    code, body = fetcher(url)
    if code != 200 or not body:
        skipped.append(f"{url}: HTTP {code or 'no response'}, not used")
        return None
    return body


def predicd_note(offset):
    if offset is None:
        return "predicd.com: time zone could not be verified against listings; its times are assumed to be Irish time"
    if offset:
        return f"predicd.com: its times were {int(offset.total_seconds() // 60)} min off Irish time; aligned using fixtures present in both sources"
    return None


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


def attach_setprob(games: list, picks: list, fetched_at) -> int:
    """Attach SetProb win probabilities to tennis fixtures whose two surnames match (either order). Returns count."""
    n = 0
    for g in games:
        if g["sport"] != "tennis" or any(m.get("name") == "SetProb" for m in g["models"]):
            continue
        for p in picks:
            if setprob.same_player(g["home"], p["a"]) and setprob.same_player(g["away"], p["b"]):
                h_is_a = True
            elif setprob.same_player(g["home"], p["b"]) and setprob.same_player(g["away"], p["a"]):
                h_is_a = False
            else:
                continue
            if p.get("time") and isinstance(g.get("kickoff"), datetime) and abs(p["time"] - g["kickoff"]) > timedelta(hours=12):
                continue   # same pair, different day
            home_wins = (p["winner"] == p["a"]) == h_is_a
            home_p = p["prob"] if home_wins else 100 - p["prob"]
            g["models"].append({"name": "SetProb", "kind": "statistical-model", "source": "setprobability.pages.dev",
                                "url": setprob.URL, "fetched_at": fetched_at,
                                "probs": {"home": home_p, "away": 100 - home_p},
                                **({"factors": hf} if (hf := setprob.home_factors(p.get("factors"), h_is_a)) else {})})
            p["used"] = True
            n += 1
            break
    return n


def setprob_only_fixtures(picks: list, existing: list, window, fetched_at) -> list:
    """Tennis matches listed by SetProb (e.g. ATP/WTA Challengers) that ESPN does not list, as fixtures sourced from
    SetProb itself. Needs a known kickoff inside the window; skipped when an ESPN fixture within 3 h already has one
    of the players (a spelling variant we failed to match), so a match never appears twice."""
    now, end = window
    espn = [g for g in existing if g.get("sport") == "tennis" and isinstance(g.get("kickoff"), datetime)]
    out = []
    for p in picks:
        t = p.get("time")
        if p.get("used") or t is None or not (now - timedelta(hours=3) <= t < end):
            continue
        if any(abs(g["kickoff"] - t) <= timedelta(hours=3)
               and any(setprob.same_player(n, x) for n in (g["home"], g["away"]) for x in (p["a"], p["b"])) for g in espn):
            continue
        label = setprob.TOUR_LABEL.get(p.get("tour"), "Tennis")
        out.append({"sport": "tennis", "competition": f"{label} - {p['tournament']}".strip(" -"),
                    "home": p["a"], "away": p["b"], "kickoff": t, "status": "scheduled", "sources": [setprob.URL],
                    "models": [{"name": "SetProb", "kind": "statistical-model", "source": "setprobability.pages.dev",
                                "url": setprob.URL, "fetched_at": fetched_at,
                                "probs": {"home": p["prob"] if p["winner"] == p["a"] else 100 - p["prob"],
                                          "away": 100 - p["prob"] if p["winner"] == p["a"] else p["prob"]},
                                **({"factors": hf} if (hf := setprob.home_factors(p.get("factors"), True)) else {})}]})
    return out


def attach_flashscore(fixtures: list, feed: list, fetch, fetched_at, workers: int = 4):
    """Match modelled football fixtures to the Flashscore feed (teams + kickoff within 30 min), fetch each match page
    and attach its preview (author, the chosen market) as fixture['preview']. Returns (stats, raw): raw maps match id
    to the preview sections, kept outside fixtures.json so a synopsis can be written from them."""
    from concurrent.futures import ThreadPoolExecutor
    pairs = []
    for f in fixtures:
        if f.get("sport") != "football" or not f.get("models") or not isinstance(f.get("kickoff"), datetime):
            continue
        for m in feed:
            if abs(m["kickoff"] - f["kickoff"]) <= timedelta(minutes=30) and (
                    teams_match(f["home"], f["away"], m["home"], m["away"]) or one_team_match(f["home"], f["away"], m["home"], m["away"])):
                pairs.append((f, m))
                break

    def get_one(pair):
        code, body = fetch(flashscore.MATCH_URL.format(id=pair[1]["id"]))
        return flashscore.parse_preview(body) if code == 200 and body else None
    with ThreadPoolExecutor(workers) as ex:
        parsed = list(ex.map(get_one, pairs))
    stats, raw = {"matched": len(pairs), "previews": 0, "picks": 0}, {}
    for (f, m), pv in zip(pairs, parsed):
        if not pv:
            continue
        pick = flashscore.parse_pick(pv["betting"], m["home"], m["away"]) if pv["betting"] else None
        stats["previews"] += 1
        stats["picks"] += bool(pick and pick["market"])
        f["preview"] = {"source": "flashscore.com", "match_id": m["id"], "url": flashscore.MATCH_URL.format(id=m["id"]),
                        "fetched_at": fetched_at, "author": pv["author"], "home": m["home"], "away": m["away"],
                        **({"pick": pick} if pick else {})}
        raw[m["id"]] = {"home": m["home"], "away": m["away"], "competition": m["competition"],
                        "kickoff": m["kickoff"].isoformat(), "url": f["preview"]["url"], "intro": pv["intro"], "sections": pv["sections"]}
    return stats, raw


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
    if preds:
        preds, offset = align(listings, preds)
        note = predicd_note(offset)
        if note:
            skipped.append(note)
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
    picks_t, tours_ok = [], 0
    for tour in setprob.TOURS:
        for d in days:
            body = get(setprob.API.format(date=f"{d[:4]}-{d[4:6]}-{d[6:]}", tour=tour), skipped)
            if body is None:
                continue
            try:
                picks_t += setprob.parse_api(json.loads(body))
                tours_ok += 1
            except ValueError:
                skipped.append(f"setprobability.pages.dev/api ({tour}): not JSON, not used")
    if not picks_t:   # feed unavailable: fall back to the ATP list in the server-rendered page
        sp_page = get(setprob.URL, skipped)
        picks_t = setprob.parse(sp_page) if sp_page else []
    if picks_t:
        got = attach_setprob(fixtures, picks_t, utc_now)
        extra = setprob_only_fixtures(picks_t, fixtures, window, utc_now)
        fixtures += extra
        skipped.append(f"setprobability.pages.dev: {len(picks_t)} tennis matches listed (ATP, WTA, Challengers): {got} matched ESPN fixtures, "
                       f"{len(extra)} added as SetProb-sourced fixtures (not on ESPN's list), the rest outside the 24 h window")
    else:
        skipped.append("setprobability.pages.dev: no tennis predictions parsed (feed or layout change?), no tennis model")

    for name, fn, path in (("mma", espn.mma, "mma/schedule"), ("golf", espn.golf, "golf/schedule")):
        url = f"{ESPN}/{path}"
        page = get(url, skipped)
        content = espn.extract(page) if page else None
        if content:
            fixtures += fn(content, url, window)

    # Flashscore: day feed (today and tomorrow) -> previews + the writer's chosen market for modelled football fixtures
    feed, fs_fail = [], 0
    for day in (0, 1):
        code, body = curl(flashscore.FEED.format(day=day), {"x-fsign": flashscore.FSIGN})
        if code == 200 and body:
            feed += flashscore.parse_feed(body)
        else:
            fs_fail += 1
            skipped.append(f"flashscore.com feed (day {day}): HTTP {code or 'no response'}, no previews for that day")
    previews_raw = {}
    if feed:
        stats, previews_raw = attach_flashscore(fixtures, feed, lambda u: curl(u, follow=True), utc_now)
        skipped.append(f"flashscore.com: {len(feed)} football matches in the feed; {stats['matched']} modelled fixtures matched, "
                       f"{stats['previews']} have a written preview, {stats['picks']} name a betting market "
                       f"(synopses are written in the daily run, see prompts/daily-research.md step 4c)")

    for src in ("cricket (ESPN/Cricinfo)", "darts", "snooker", "boxing", "GAA", "horse and greyhound racing", "esports"):
        skipped.append(f"{src}: no collector yet, not covered in this run")
    return {"generated_at": now.isoformat(), "skipped": skipped, "fixtures": fixtures, "previews_raw": previews_raw}


def _json(o):
    if isinstance(o, datetime):
        return o.astimezone(timezone.utc).isoformat()
    raise TypeError(type(o))


if __name__ == "__main__":
    data = collect(datetime.now(DUB))
    raw = data.pop("previews_raw", {})
    os.makedirs("out", exist_ok=True)
    with open("out/previews_raw.json", "w") as f:      # preview text for writing synopses; not committed (out/ is gitignored)
        json.dump(raw, f, indent=1, ensure_ascii=False)
    with open(sys.argv[1], "w") as f:
        json.dump(data, f, indent=1, default=_json)
    print(f"{len(data['fixtures'])} fixtures, {len(data['skipped'])} skipped notes")
