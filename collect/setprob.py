"""Parse setprobability.pages.dev (SetProb: statistical tennis win probabilities).
The server-rendered page lists today's ATP matches in <div id="ssr-matches">; WTA/Challenger and 'Tomorrow'
load via JavaScript and are not collected here."""
import html as H
import re
import unicodedata

URL = "https://setprobability.pages.dev/"
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
