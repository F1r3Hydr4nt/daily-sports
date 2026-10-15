"""Merge football listings (live-footballontv) with Predicd probabilities."""
import difflib
import re
import unicodedata
from datetime import timedelta

from src.dedupe import canon

ALIASES = {"paris saintgermain": "psg", "oudheverlee leuven": "oh leuven", "servette chenois": "servette",
           "inter milan": "inter", "man utd": "manchester united",
           "borussia mgladbach": "borussia monchengladbach", "betis sevilla": "real betis", "qpr": "queens park rangers", "west brom": "west bromwich albion"}
# Club-name decoration that differs between sources ("Málaga" vs "Málaga CF", "Stade Brest" vs "Brest").
NOISE = {"fc", "cf", "sc", "ac", "afc", "club", "calcio", "fotball", "football", "sco", "us", "ud", "cd", "ca", "sv",
         "kv", "krc", "kaa", "rc", "bk", "sk", "fk", "nk", "hnk", "sg", "de", "stade", "olympique", "deportivo"}
TOLERANCE = timedelta(minutes=30)
FINISHED_AFTER = timedelta(minutes=100)  # a match started longer ago than this is treated as finished


def norm(name: str) -> str:
    name = re.sub(r"\(.*?\)", "", name).replace("ß", "ss")
    n = unicodedata.normalize("NFKD", name.replace("ø", "o").replace("Ø", "O")).encode("ascii", "ignore").decode().lower()
    n = re.sub(r"\b(women|w)$", "", n.strip()).strip()
    n = canon(n).replace("republic of ", "").replace("wien", "vienna").replace("-", "")
    return ALIASES.get(n, n)


def _sim(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def _tokens(name: str) -> set:
    return {t for t in norm(name).split() if t not in NOISE and not re.fullmatch(r"\d{4}", t)}


def same_team(a: str, b: str) -> bool:
    """Same club despite naming differences: token subset (ignoring noise words) or close spelling.
    Youth (U18/U21) and reserve (II/B) sides only match the same kind of side."""
    ta, tb = _tokens(a), _tokens(b)
    youth = lambda t: {x for x in t if re.fullmatch(r"u\d\d|ii|iii|b", x)}  # age group / reserve side
    if youth(ta) != youth(tb):
        return False
    small, big = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    if small and small <= big and max(len(x) for x in small) >= 4:
        return True
    # Neither name contains the other: allow spelling differences, but not different words ("United" vs "City").
    close = lambda x, ys: any(difflib.SequenceMatcher(None, x, y).ratio() >= 0.8 for y in ys)
    da, db = ta - tb, tb - ta
    return _sim(a, b) > 0.7 and all(close(x, db) for x in da) and all(close(y, da) for y in db)


def _wild(name: str) -> bool:
    """A name with no informative words left (e.g. a listing truncated to "SG"): it cannot contradict anything."""
    return not _tokens(name)


def teams_match(p_home, p_away, f_home, f_away) -> bool:
    """Both teams match; a truncated name counts as a match if the other team matches properly."""
    hm, am = same_team(p_home, f_home), same_team(p_away, f_away)
    hw = _wild(p_home) or _wild(f_home)
    aw = _wild(p_away) or _wild(f_away)
    return (hm or hw) and (am or aw) and (hm or am)


SAME_KICKOFF = timedelta(minutes=5)


def _kind(name: str) -> set:
    return {x for x in _tokens(name) if re.fullmatch(r"u\d\d|ii|iii|b", x)}


def one_team_match(p_home, p_away, f_home, f_away) -> bool:
    """A club cannot play two games at once: one team matching at (nearly) the same kickoff identifies the fixture
    even when the other side is spelled very differently ("Crvena zvezda" vs "Red Star Belgrade").
    Youth/reserve sides must still agree."""
    hm, am = same_team(p_home, f_home), same_team(p_away, f_away)
    if hm and not _wild(p_home) and not _wild(f_home):
        return _kind(p_away) == _kind(f_away)
    if am and not _wild(p_away) and not _wild(f_away):
        return _kind(p_home) == _kind(f_home)
    return False


def _model(p, fetched_at=None):
    return {"name": "Predicd", "kind": "statistical-model", "source": "predicd.com",
            "url": "https://www.predicd.com/en/football/", "fetched_at": fetched_at, "probs": p["probs"]}


def merge(listings: list, preds: list, now, fetched_at=None) -> list:
    end = now + timedelta(hours=24)
    fetched_at = fetched_at or now
    out, used = [], set()
    for f in listings:
        t = f["kickoff"]
        if t >= end:
            continue
        status = "scheduled"
        if t < now:
            if now - t >= FINISHED_AFTER:
                continue
            status = "live"
        models = []
        for i, p in enumerate(preds):
            if i in used:
                continue
            dt = abs(p["kickoff"] - t)
            if (dt <= TOLERANCE and teams_match(p["home"], p["away"], f["home"], f["away"])) or \
                    (dt <= SAME_KICKOFF and one_team_match(p["home"], p["away"], f["home"], f["away"])):
                used.add(i)
                models.append(_model(p, fetched_at))
        out.append({**f, "status": status, "models": models})
    for i, p in enumerate(preds):
        if i not in used and now <= p["kickoff"] < end:
            out.append({"sport": "football", "competition": p["competition"], "home": p["home"], "away": p["away"],
                        "kickoff": p["kickoff"], "status": "scheduled", "sources": [_model(p)["url"]],
                        "models": [_model(p, fetched_at)]})
    return sorted(out, key=lambda x: x["kickoff"])


def align(listings: list, preds: list):
    """Predicd's time zone has varied between fetches (Irish time, then UTC).  Estimate the shift from
    fixtures present in both sources and apply it.  Returns (preds, offset); offset is None when unknown."""
    diffs = []
    for p in preds:
        for f in listings:
            if _sim(p["home"], f["home"]) > 0.8 and _sim(p["away"], f["away"]) > 0.8:
                d = f["kickoff"] - p["kickoff"]
                if abs(d) <= timedelta(hours=14):
                    diffs.append(d)
                break
    if not diffs:
        return preds, None
    mode = max(set(diffs), key=diffs.count)
    if diffs.count(mode) * 2 < len(diffs):
        return preds, None
    return [{**p, "kickoff": p["kickoff"] + mode} for p in preds], mode
