"""Parse predicd.com/en/football (statistical win/draw/loss model; times are Irish time)."""
import html as H
import re
from datetime import datetime
from zoneinfo import ZoneInfo

DUB = ZoneInfo("Europe/Dublin")
URL = "https://www.predicd.com/en/football/"


def html_to_text(page: str) -> str:
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", page, flags=re.S)
    t = re.sub(r"<[^>]+>", "|", t)
    return H.unescape(re.sub(r"\s*\|[\s|]*", "|", t))


def parse_text(text: str, year: int) -> list:
    out = []
    for part in re.split(r"\|(?=\d\d\.\d\d\. \d\d:\d\d\|)", text)[1:]:
        m = re.match(r"(\d\d)\.(\d\d)\. (\d\d):(\d\d)\|(?:-->\|)?(.*?)\|(?:-->\|)?(.*?)\|-\|", part)
        if not m:
            continue
        d, mo, hh, mm, home, away = m.groups()
        comp = re.search(r"Competition:\|(.*?)\|", part)
        w = re.search(r"Win Probability:\|(\d+)%?\|(\d+)%?\|(\d+)%?", part)
        if not w:
            continue
        out.append({"competition": comp.group(1) if comp else "", "home": home, "away": away,
                    "kickoff": datetime(year, int(mo), int(d), int(hh), int(mm), tzinfo=DUB),
                    "probs": {"home": int(w.group(1)), "draw": int(w.group(2)), "away": int(w.group(3))}})
    return out


def parse(page: str, year: int) -> list:
    return parse_text(html_to_text(page), year)
