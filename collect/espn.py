"""ESPN pages embed their data as JSON in window['__espnfitt__']."""
import json
import re
from datetime import datetime, timedelta, timezone

FITT = re.compile(r"window\['__espnfitt__'\]\s*=\s*(\{.*?\});</script>", re.S)
TEAM_LEAGUES = {  # path -> (sport, label)
    "nhl": ("nhl", "NHL"), "nfl": ("nfl", "NFL"), "nba": ("nba", "NBA"), "wnba": ("wnba", "WNBA"), "mlb": ("mlb", "MLB"),
    "college-football": ("ncaa", "NCAA Football"),
    "mens-college-basketball": ("ncaa", "NCAA Men's Basketball"),
    "womens-college-basketball": ("ncaa", "NCAA Women's Basketball"),
}


def extract(page: str):
    m = FITT.search(page)
    return json.loads(m.group(1))["page"]["content"] if m else None


def _t(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)


def _status(state: str, start: datetime, now: datetime) -> str:
    return "live" if state == "in" or start < now else "scheduled"


def team_events(content: dict, sport: str, label: str, url: str, window) -> list:
    now, end = window
    out, seen = [], set()
    for events in content.get("events", {}).values():
        for e in events:
            t = _t(e["date"])
            state = (e.get("status") or {}).get("state", "")
            if e.get("completed") or state == "post" or e["id"] in seen or not (now - timedelta(hours=4) <= t < end):
                continue
            home = next(c for c in e["competitors"] if c.get("isHome"))
            away = next(c for c in e["competitors"] if not c.get("isHome"))
            seen.add(e["id"])
            out.append({"sport": sport, "competition": label, "home": home["displayName"], "away": away["displayName"],
                        "kickoff": t, "status": _status(state, t, now), "sources": [url], "models": []})
    return out


def tennis(content: dict, url: str, window) -> list:
    now, end = window
    sb = content["scoreboard"]
    where = {cid: (t["name"], g["name"]) for t in sb["tournaments"] for g in t["groupings"] for cid in g["competitionIds"]}
    out = []
    for cid, c in sb["competitions"].items():
        t = _t(c["date"])
        state = c["status"]["state"]
        names = [x.get("nm") for x in c["competitors"]]
        if state == "post" or len(names) < 2 or None in names or not (now - timedelta(hours=3) <= t < end):
            continue
        tour, grp = where.get(cid, ("Tennis", ""))
        out.append({"sport": "tennis", "competition": f"{tour} - {grp} {c.get('note', '')}".strip(" -"),
                    "home": names[0], "away": names[1], "kickoff": t, "status": _status(state, t, now), "sources": [url], "models": []})
    return out


def rugby(content: dict, url: str, window) -> list:
    now, end = window
    out = []
    for lg in content["scoreboard"].get("gmsByLeague", []):
        for e in lg["evts"]:
            t = _t(e["date"])
            state = (e.get("status") or {}).get("state", "") if isinstance(e.get("status"), dict) else ""
            if e.get("completed") or state == "post" or not (now - timedelta(hours=3) <= t < end):
                continue
            home = next(c for c in e["competitors"] if c.get("isHome"))
            away = next(c for c in e["competitors"] if not c.get("isHome"))
            out.append({"sport": "rugby", "competition": lg["league"]["name"], "home": home["displayName"],
                        "away": away["displayName"], "kickoff": t, "status": _status(state, t, now), "sources": [url], "models": []})
    return out


def mma(content: dict, url: str, window) -> list:
    now, end = window
    out = []
    for events in content["events"].values():
        for e in events:
            t = _t(e["date"])
            if e["status"]["state"] != "post" and now <= t < end:
                out.append({"sport": "mma", "competition": e["name"], "home": e["name"], "away": "Event card",
                            "kickoff": t, "status": "scheduled", "sources": [url], "models": []})
    return out


def golf(content: dict, url: str, window) -> list:
    now, end = window
    out = []
    for e in content["events"]:
        if e["status"] == "in" and e["startDate"] <= end.strftime("%Y-%m-%dT%H:%MZ") and e["endDate"] >= now.strftime("%Y-%m-%dT%H:%MZ"):
            venue = e["locations"][0]["venue"]["fullName"] if e.get("locations") else ""
            out.append({"sport": "golf", "competition": f"Tournament in progress, {e['date']}, {venue}".strip(", "),
                        "home": e["name"], "away": "Field", "kickoff": _t(e["startDate"]), "status": "live", "sources": [url], "models": []})
    return out
