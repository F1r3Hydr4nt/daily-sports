from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from collect.football import merge
from collect import run

DUB = ZoneInfo("Europe/Dublin")
NOW = datetime(2026, 10, 1, 16, 10, tzinfo=DUB)

def fx(h, a, t, comp="Cup"):
    return {"sport": "football", "competition": comp, "home": h, "away": a, "kickoff": t, "sources": ["fotv"]}

def pr(h, a, t, probs=None):
    return {"competition": "C", "home": h, "away": a, "kickoff": t,
            "probs": probs or {"home": 50, "draw": 25, "away": 25}}

T = datetime(2026, 10, 1, 19, 45, tzinfo=DUB)

def test_merge_attaches_predicd_to_matching_listing():
    out = merge([fx("Republic of Ireland", "Austria", T)], [pr("Ireland", "Austria", T)], NOW)
    assert len(out) == 1 and out[0]["models"][0]["source"] == "predicd.com"
    assert out[0]["kickoff"].tzinfo is not None

def test_merge_handles_women_and_diacritics():
    out = merge([fx("HB Koge Women", "Servette Women", T)], [pr("HB Køge W", "Servette FC Chênois W", T)], NOW)
    assert len(out) == 1 and out[0]["models"]

def test_merge_adds_predicd_only_fixtures_in_window():
    out = merge([], [pr("A", "B", T), pr("C", "D", NOW - timedelta(hours=3))], NOW)
    assert [(o["home"], o["away"]) for o in out] == [("A", "B")]

def test_merge_drops_finished_and_marks_live():
    live = fx("L", "M", NOW - timedelta(minutes=30))
    done = fx("X", "Y", NOW - timedelta(hours=5))
    out = {o["home"]: o for o in merge([live, done], [], NOW)}
    assert "X" not in out and out["L"]["status"] == "live"

def test_merge_drops_beyond_24h():
    assert merge([fx("A", "B", NOW + timedelta(hours=25))], [], NOW) == []

def test_merge_different_times_not_matched():
    out = merge([fx("A", "B", T)], [pr("A", "B", T + timedelta(hours=3))], NOW)
    assert len(out) == 2

def test_attach_covers_scores_and_skip_unpublished():
    games = [{"sport": "nfl", "home": "Cleveland Browns", "away": "Pittsburgh Steelers", "models": []},
             {"sport": "wnba", "home": "Las Vegas Aces", "away": "Indiana Fever", "models": []}]
    picks = {"nfl": [{"away": "Pittsburgh", "home": "Cleveland", "away_score": 18.9, "home_score": 17.59}],
             "wnba": [{"away": "Indiana", "home": "Las Vegas", "away_score": 0.0, "home_score": 0.0}]}
    notes = run.attach_covers(games, picks, fetched_at=NOW)
    assert games[0]["models"][0]["score"] == {"home": 17.59, "away": 18.9}
    assert games[1]["models"] == [] and any("wnba" in n.lower() for n in notes)

def test_fetch_failure_recorded_not_raised():
    skipped = []
    assert run.get("https://example.invalid/", skipped, fetcher=lambda u: (403, "")) is None
    assert skipped and "403" in skipped[0]
    assert run.get("u", skipped, fetcher=lambda u: (200, "ok")) == "ok"
