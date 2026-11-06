import json
from datetime import datetime
from zoneinfo import ZoneInfo

from src.build import build
from src.window import filter_modelled

NOW = datetime(2026, 10, 1, 9, 0, tzinfo=ZoneInfo("Europe/Dublin"))


def test_filter_modelled_keeps_only_fixtures_with_a_model():
    a = {"home": "A", "away": "B", "models": [{"name": "m"}]}
    b = {"home": "C", "away": "D", "models": []}
    c = {"home": "E", "away": "F"}
    assert filter_modelled([a, b, c]) == [a]


def _fixtures(tmp_path):
    ts = "2026-10-01T18:30:00+00:00"
    m = {"name": "Predicd", "kind": "statistical-model", "source": "predicd.com", "url": "https://x/",
         "fetched_at": "2026-10-01T08:00:00+00:00", "probs": {"home": 50, "draw": 25, "away": 25}}
    base = {"competition": "C", "kickoff": ts, "status": "scheduled", "sources": ["https://x/"]}
    data = {"fixtures": [
        {**base, "sport": "football", "home": "Modelled FC", "away": "Other FC", "models": [m]},
        {**base, "sport": "tennis", "home": "Unmodelled P", "away": "Unmodelled Q", "models": []},
    ], "skipped": []}
    p = tmp_path / "f.json"
    p.write_text(json.dumps(data))
    return str(p)


def test_build_hides_fixtures_without_a_model_and_says_so(tmp_path):
    out = tmp_path / "i.html"
    r = build(_fixtures(tmp_path), str(out), NOW)
    html = out.read_text()
    assert r["count"] == 1 and r["hidden"] == 1
    assert "Modelled FC" in html and "Unmodelled P" not in html
    assert "no model available" not in html
    assert "1 fixture without a model prediction is not shown" in html
    assert "Tennis" not in html


def test_build_can_show_everything(tmp_path):
    out = tmp_path / "i.html"
    r = build(_fixtures(tmp_path), str(out), NOW, models_only=False)
    assert r["count"] == 2 and "Unmodelled P" in out.read_text()
