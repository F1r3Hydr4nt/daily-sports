"""Parse setprobability.pages.dev (SetProb: statistical tennis win probabilities).
The server-rendered page lists today's ATP matches in <div id="ssr-matches">; WTA/Challenger and 'Tomorrow'
load via JavaScript and are not collected here."""
import html as H
import re
import unicodedata
from datetime import datetime

URL = "https://setprobability.pages.dev/"
API = "https://setprobability.pages.dev/api/fixtures?date={date}&tour={tour}"   # the site's own endpoint (what its page loads)
TOURS = ("atp", "wta", "atp-challenger", "wta-challenger")
TOUR_LABEL = {"atp": "ATP", "wta": "WTA", "atp-challenger": "ATP Challenger", "wta-challenger": "WTA Challenger"}
CARD = re.compile(r'<div class="ssr-tourn">([^<]*)</div>\s*<div class="ssr-players">([^<]*?) vs ([^<]*)</div>\s*'
                  r'<div class="ssr-pick">Prediction: ([^<]*?) to win \((\d+)% probability\)</div>')


def parse(page: str) -> list:
    out = []
    for m in CARD.finditer(page):
        t, a, b, w, p = (H.unescape(x).strip() for x in m.groups())
        if w not in (a, b) or not 0 < int(p) < 100:
            continue
        out.append({"tournament": t, "a": a, "b": b, "winner": w, "prob": int(p)})
    return out


def surname(name: str) -> str:
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    parts = re.findall(r"[a-z']+", s)
    return parts[-1] if parts else ""


def parse_api(rows) -> list:
    """Rows from /api/fixtures. Only the predicted winner and its probability are read: the feed also carries
    betting-market odds fields, which this project never collects."""
    out = []
    if not isinstance(rows, list):
        return out
    for r in rows:
        try:
            a, b, w, p = r["p1_name"], r["p2_name"], r["predicted_winner"], r["confidence"]
        except (KeyError, TypeError):
            continue
        if not (a and b) or w not in (a, b) or not isinstance(p, (int, float)) or not 0 < p < 100:
            continue
        try:
            t = datetime.fromisoformat(r["match_time"])
        except (KeyError, TypeError, ValueError):
            t = None
        out.append({"tournament": r.get("tournament") or "", "a": a, "b": b, "winner": w, "prob": int(p), "tour": r.get("tour") or "", "time": t})
    return out


def tokens(name: str) -> list:
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    return re.findall(r"[a-z']+", s)


def same_player(x: str, y: str) -> bool:
    """Same surname, tolerating double surnames written in full by one source and shortened by the other
    ('Irene Burillo' / 'Irene Burillo Escorihuela'); first names alone never match."""
    tx, ty = tokens(x), tokens(y)
    return bool(tx and ty) and (tx[-1] in ty[1:] or ty[-1] in tx[1:] or tx[-1] == ty[-1])
