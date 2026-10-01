import pytest
from src.normalise import normalise, consensus, flags

def test_rescales_to_100():
    p = normalise({"home": 50, "draw": 26, "away": 25})  # sums 101
    assert sum(p.values()) == pytest.approx(100)
    assert p["home"] == pytest.approx(50 / 101 * 100)

def test_two_way():
    assert normalise({"a": 60, "b": 41}) == pytest.approx({"a": 59.4059, "b": 40.5941}, abs=1e-3)

def test_rejects_negative_or_zero_total():
    with pytest.raises(ValueError):
        normalise({"a": 0, "b": 0})
    with pytest.raises(ValueError):
        normalise({"a": -1, "b": 2})

def test_consensus_and_spread():
    c = consensus([{"home": 60, "away": 40}, {"home": 50, "away": 50}])
    assert c["mean"] == {"home": 55, "away": 45}
    assert c["spread"] == {"home": 10, "away": 10}

def test_flag_boundaries_vs_consensus():
    base = {"home": 50, "away": 50}
    assert flags([base, {"home": 54.99, "away": 45.01}])["consensus_gap"] is False
    assert flags([base, {"home": 60, "away": 40}])["consensus_gap"] is True

def test_model_spread_flag_at_10():
    assert flags([{"home": 50, "away": 50}, {"home": 60, "away": 40}])["model_spread"] is True
    assert flags([{"home": 50, "away": 50}, {"home": 59.9, "away": 40.1}])["model_spread"] is False

def test_single_model_low_confidence_no_flags():
    f = flags([{"home": 70, "away": 30}])
    assert f["low_confidence"] is True and not f["consensus_gap"] and not f["model_spread"]
