"""Merge football listings (live-footballontv) with Predicd probabilities."""
import difflib
import re
import unicodedata
from datetime import timedelta

from src.dedupe import canon

ALIASES = {"paris saintgermain": "psg", "oudheverlee leuven": "oh leuven", "servette chenois": "servette",
           "inter milan": "inter", "man utd": "manchester united"}
TOLERANCE = timedelta(minutes=30)
FINISHED_AFTER = timedelta(minutes=100)  # a match started longer ago than this is treated as finished


def norm(name: str) -> str:
    n = unicodedata.normalize("NFKD", name.replace("ø", "o").replace("Ø", "O")).encode("ascii", "ignore").decode().lower()
    n = re.sub(r"\b(women|w)$", "", n.strip()).strip()
    n = canon(n).replace("republic of ", "").replace("wien", "vienna").replace("-", "")
    return ALIASES.get(n, n)


def _sim(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


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
            if abs(p["kickoff"] - t) <= TOLERANCE and _sim(p["home"], f["home"]) > 0.7 and _sim(p["away"], f["away"]) > 0.7:
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
