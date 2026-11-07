import json
from datetime import datetime
from zoneinfo import ZoneInfo

from src.build import build

NOW = datetime(2026, 10, 1, 9, 0, tzinfo=ZoneInfo("Europe/Dublin"))


def _fx(tmp_path):
    m = lambda **k: {"name": "M", "kind": "statistical-model", "source": "s", "url": "https://x/",
                     "fetched_at": "2026-10-01T08:00:00+00:00", **k}
    base = {"competition": "C", "kickoff": "2026-10-01T18:30:00+00:00", "status": "scheduled", "sources": []}
    fx = [
        {**base, "sport": "football", "home": "Big FC", "away": "Small FC",
         "models": [m(probs={"home": 86, "draw": 9, "away": 5})]},
        {**base, "sport": "football", "home": "Even FC", "away": "Level FC",
         "models": [m(probs={"home": 35, "draw": 30, "away": 35})]},
        {**base, "sport": "nhl", "home": "Clear Team", "away": "Other Team",
         "models": [m(score={"home": 3.7, "away": 2.2})]},
        {**base, "sport": "nhl", "home": "Close Team", "away": "Tight Team",
         "models": [m(score={"home": 3.1, "away": 3.0})]},
    ]
    p = tmp_path / "f.json"
    p.write_text(json.dumps({"fixtures": fx, "skipped": []}))
    return str(p)


def test_rows_carry_margin_and_controls_have_defaults(tmp_path):
    out = tmp_path / "i.html"
    build(_fx(tmp_path), str(out), NOW)
    html = out.read_text()
    assert 'id="min-football"' in html and 'value="2"' in html
    assert 'id="min-nhl"' in html and 'value="0.75"' in html
    assert 'data-sport="football"' in html and 'data-margin="' in html
    assert "Derived score" in html          # football score is derived from the probabilities
    assert "predicted score" in html        # NHL score is published
    assert "<script>" in html and "min-football" in html


def test_every_modelled_row_is_in_the_html_so_controls_can_loosen_the_filter(tmp_path):
    out = tmp_path / "i.html"
    build(_fx(tmp_path), str(out), NOW)
    html = out.read_text()
    for name in ("Big FC", "Even FC", "Clear Team", "Close Team"):
        assert name in html
