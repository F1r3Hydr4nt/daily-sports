"""Parse live-footballontv.com listings (UK/Irish local time = Europe/Dublin)."""
import html as H
import re
from datetime import datetime
from zoneinfo import ZoneInfo

DUB = ZoneInfo("Europe/Dublin")
MONTHS = {m: i for i, m in enumerate(
    "January February March April May June July August September October November December".split(), 1)}
HEAD = re.compile(r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday) (\d+)(?:st|nd|rd|th) (\w+) (\d{4})")
FIXTURE = re.compile(r'fixture__time">(\d\d):(\d\d)</div><div class="fixture__teams">(.*?)</div>'
                     r'<div class="fixture__competition">(.*?)</div>')


def parse(page: str) -> list:
    heads = [(m.start(), datetime(int(m.group(3)), MONTHS[m.group(2)], int(m.group(1))).date())
             for m in HEAD.finditer(page)]
    out = []
    for i, (pos, day) in enumerate(heads):
        end = heads[i + 1][0] if i + 1 < len(heads) else len(page)
        for m in FIXTURE.finditer(page[pos:end]):
            hh, mm, teams, comp = m.groups()
            teams = H.unescape(teams).strip()
            if " v " not in teams:
                continue
            home, away = (t.strip() for t in teams.split(" v ", 1))
            out.append({"sport": "football", "competition": H.unescape(comp).strip(), "home": home, "away": away,
                        "kickoff": datetime(day.year, day.month, day.day, int(hh), int(mm), tzinfo=DUB),
                        "sources": ["https://www.live-footballontv.com/"]})
    return out
