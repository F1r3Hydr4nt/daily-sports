from datetime import datetime, timezone
import pytest
from src.schema import parse_fixture

def good():
    return {"sport": "football", "competition": "PL", "home": "A", "away": "B",
            "kickoff": datetime(2026, 10, 1, 19, 0, tzinfo=timezone.utc), "status": "scheduled",
            "models": [{"name": "m", "kind": "statistical-model", "source": "s", "url": "u",
                        "fetched_at": datetime(2026, 10, 1, 8, tzinfo=timezone.utc),
                        "probs": {"home": 50, "away": 50}}]}

def test_valid_parses():
    assert parse_fixture(good())["home"] == "A"

@pytest.mark.parametrize("mut", [
    lambda d: d.pop("kickoff"),
    lambda d: d.update(kickoff=datetime(2026, 10, 1, 19, 0)),
    lambda d: d.update(status="weird"),
    lambda d: d["models"][0].update(probs={"home": -5, "away": 105}),
    lambda d: d["models"][0].update(kind="vibes"),
    lambda d: d["models"][0].pop("source"),
])
def test_invalid_rejected(mut):
    d = good(); mut(d)
    with pytest.raises(ValueError):
        parse_fixture(d)


def score_model(**kw):
    m = {"name": "Odds Shark", "kind": "statistical-model", "source": "covers.com", "url": "u",
         "fetched_at": datetime(2026, 10, 1, 8, tzinfo=timezone.utc), "score": {"home": 17.59, "away": 18.9}}
    m.update(kw)
    return m


def test_score_only_model_valid():
    d = good(); d["models"] = [score_model()]
    assert parse_fixture(d)

@pytest.mark.parametrize("bad", [
    {"score": {"home": 0.0, "away": 0.0}},   # 0.00 = not published
    {"score": {"home": -1, "away": 3}},
    {"score": {"home": 1}},
])
def test_bad_score_rejected(bad):
    d = good(); d["models"] = [score_model(**bad)]
    with pytest.raises(ValueError):
        parse_fixture(d)

def test_model_needs_probs_or_score():
    d = good(); m = score_model(); m.pop("score"); d["models"] = [m]
    with pytest.raises(ValueError):
        parse_fixture(d)
