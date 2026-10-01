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
