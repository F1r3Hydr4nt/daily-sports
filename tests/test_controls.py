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
    assert "derived from win probabilities" in html   # football score is derived from the probabilities
    assert "published by M" in html                   # NHL score is published by the source
    assert "<script>" in html and "min-football" in html


def test_every_modelled_row_is_in_the_html_so_controls_can_loosen_the_filter(tmp_path):
    out = tmp_path / "i.html"
    build(_fx(tmp_path), str(out), NOW)
    html = out.read_text()
    for name in ("Big FC", "Even FC", "Clear Team", "Close Team"):
        assert name in html


def _row(html, name):
    i = html.index(name)
    return html[html.rindex("<tr", 0, i):i]


def test_default_thresholds_are_applied_in_the_html_itself(tmp_path):
    """Hidden by default even if the page's JavaScript never runs."""
    out = tmp_path / "i.html"
    build(_fx(tmp_path), str(out), NOW)
    html = out.read_text()
    assert 'class="off"' not in _row(html, "Big FC") and 'class="off"' not in _row(html, "Clear Team")
    assert 'class="off"' in _row(html, "Even FC") and 'class="off"' in _row(html, "Close Team")
    assert "Showing 2 of 4" in html


def test_score_is_its_own_prominent_column(tmp_path):
    out = tmp_path / "i.html"
    build(_fx(tmp_path), str(out), NOW)
    html = out.read_text()
    assert "<th>Predicted score</th>" in html
    assert '<div class="score">3.7 - 2.2</div>' in html
    assert "margin 1.5" in html


def test_rows_default_to_largest_margin_first(tmp_path):
    from src.score import predicted_score
    out = tmp_path / "i.html"
    p = json.loads(open(_fx(tmp_path)).read())
    m = p["fixtures"][0]["models"][0]
    mk = lambda home, probs: {**p["fixtures"][0], "home": home, "models": [{**m, "probs": probs}]}
    p["fixtures"] = [mk("Midland United", {"home": 70, "draw": 18, "away": 12}),
                     mk("Hugeton Rovers", {"home": 92, "draw": 6, "away": 2}),
                     mk("Smallville Town", {"home": 45, "draw": 30, "away": 25})]
    f = tmp_path / "s.json"
    f.write_text(json.dumps(p))
    build(str(f), str(out), NOW)
    html = out.read_text()
    order = sorted(["Midland United", "Hugeton Rovers", "Smallville Town"], key=html.index)
    margins = {n: abs(predicted_score(x)["margin"]) for n, x in zip(["Midland United", "Hugeton Rovers", "Smallville Town"], p["fixtures"])}
    assert order == sorted(margins, key=margins.get, reverse=True)
    assert 'id="sort-by"' in html


def test_controls_are_not_a_form(tmp_path):
    out = tmp_path / "i.html"
    build(_fx(tmp_path), str(out), NOW)
    assert "<form" not in out.read_text()
