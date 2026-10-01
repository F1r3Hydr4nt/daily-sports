from datetime import datetime, timezone, timedelta
from src.dedupe import dedupe

T = datetime(2026, 10, 1, 19, 0, tzinfo=timezone.utc)

def fx(h, a, t=T, models=None, src="x"):
    return {"sport": "football", "home": h, "away": a, "kickoff": t, "status": "scheduled",
            "models": models or [], "sources": [src]}

def test_alias_merge_combines_models_and_sources():
    a = fx("Man Utd", "Spurs", models=[{"name": "m1"}], src="feed")
    b = fx("Manchester United", "Tottenham Hotspur", T + timedelta(minutes=5), [{"name": "m2"}], "web")
    out = dedupe([a, b])
    assert len(out) == 1
    assert {m["name"] for m in out[0]["models"]} == {"m1", "m2"}
    assert set(out[0]["sources"]) == {"feed", "web"}

def test_different_matches_kept():
    assert len(dedupe([fx("A", "B"), fx("C", "D")])) == 2

def test_same_teams_far_apart_times_not_merged():
    assert len(dedupe([fx("A", "B"), fx("A", "B", T + timedelta(days=1))])) == 2

def test_fuzzy_suffix_fc():
    assert len(dedupe([fx("Arsenal FC", "Chelsea"), fx("Arsenal", "Chelsea FC")])) == 1
