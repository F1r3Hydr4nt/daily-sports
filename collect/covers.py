"""Parse covers.com/picks/<league> (Odds Shark computer picks: predicted scores, not probabilities)."""
import html as H
import re

from .predicd import html_to_text

PICK = re.compile(r"\|([A-Za-z.' ]+) @ ([A-Za-z.' ]+)\|([^|]*)\|Matchup Stats\|Computer Picks\|Trends\|Predicted Score\|"
                  r"(\w+)\|\w+\|(?:[^|\d]*\|)?([\d.]+)\|@\|(?:[^|\d]*\|)?([\d.]+)\|(\w+)")


def parse_text(text: str) -> list:
    return [{"away": m.group(1).strip(), "home": m.group(2).strip(),
             "away_score": float(m.group(5)), "home_score": float(m.group(6))} for m in PICK.finditer(text)]


def parse(page: str) -> list:
    return parse_text(html_to_text(page))


def published(picks: list) -> list:
    """0.00 predicted scores mean Odds Shark has not published yet."""
    return [p for p in picks if p["away_score"] or p["home_score"]]


def _n(x: str) -> str:
    return x.lower().replace("n.y.", "new york").replace("ny ", "new york ").replace("l.a.", "los angeles").replace(".", "")


def same_team(short: str, full: str) -> bool:
    short, full = _n(short), _n(full)
    return full.startswith(short) or short in full
