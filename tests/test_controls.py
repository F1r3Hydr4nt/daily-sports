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


def test_each_filtered_table_has_its_own_control_directly_above_it(tmp_path):
    out = tmp_path / "i.html"
    build(_fx(tmp_path), str(out), NOW)
    html = out.read_text()
    for sport, box in (("football", "min-football"), ("nhl", "min-nhl")):
        sec = html[html.index(f'id="sport-{sport}"'):]
        sec = sec[:sec.index("</section>")]
        assert f'id="{box}"' in sec and sec.index(f'id="{box}"') < sec.index("<table>")
    assert 'class="scorebox' in html           # highlighted score chip in the rows
    assert "Layout v6" in html                 # visible stamp so a stale cached copy is obvious


def test_page_check_flags_missing_controls_or_scores():
    from src.validate import check_page
    good = '<th>Predicted score</th><div class="scorebox"></div><input id="min-football"><input id="min-nhl">'
    assert check_page(good, {"football", "nhl"}) == []
    errs = check_page("<table></table>", {"football", "nhl"})
    assert any("predicted score" in e for e in errs) and any("min-football" in e for e in errs)
    assert any("min-tennis" in e for e in check_page("<table></table>", {"tennis"}))   # tennis has a gap control now
    assert check_page('<input id="min-tennis">', {"tennis"}) == []


def _nfl_fx(tmp_path):
    m = {"name": "Odds Shark computer pick", "kind": "statistical-model", "source": "covers.com", "url": "https://x/",
         "fetched_at": "2026-10-01T08:00:00+00:00"}
    base = {"competition": "NFL", "kickoff": "2026-10-01T18:30:00+00:00", "status": "scheduled", "sources": [], "sport": "nfl"}
    fx = [{**base, "home": "Big Margin Team", "away": "Other A", "models": [{**m, "score": {"home": 27.9, "away": 17.2}}]},
          {**base, "home": "Close Game Team", "away": "Other B", "models": [{**m, "score": {"home": 22.0, "away": 20.5}}]}]
    p = tmp_path / "n.json"
    p.write_text(json.dumps({"fixtures": fx, "skipped": []}))
    return str(p)


def test_nfl_has_its_own_margin_control_defaulting_to_6_5_points(tmp_path):
    out = tmp_path / "i.html"
    r = build(_nfl_fx(tmp_path), str(out), NOW)
    html = out.read_text()
    sec = html[html.index('id="sport-nfl"'):]
    sec = sec[:sec.index("</section>")]
    assert 'id="min-nfl"' in sec and 'value="6.5"' in sec and "points" in sec
    assert sec.index('id="min-nfl"') < sec.index("<table>")
    assert 'class="off"' not in _row(html, "Big Margin Team")      # 10.7 >= 6.5
    assert 'class="off"' in _row(html, "Close Game Team")         # 1.5 < 6.5
    assert "Showing 1 of 2" in html and r["ok"]


def test_page_check_requires_the_nfl_control_when_nfl_is_shown():
    from src.validate import check_page
    base = '<th>Predicted score</th><div class="scorebox"></div><input id="min-football"><input id="min-nhl">'
    assert any("min-nfl" in e for e in check_page(base, {"nfl"}))
    assert check_page(base + '<input id="min-nfl">', {"nfl"}) == []


def test_a_filtered_out_section_keeps_its_control_visible(tmp_path):
    """If every row is below the default margin the control must still be on the page and not hidden."""
    out = tmp_path / "i.html"
    p = json.loads(open(_fx(tmp_path)).read())
    p["fixtures"] = [f for f in p["fixtures"] if f["home"] in ("Even FC", "Close Team")]
    f = tmp_path / "q.json"
    f.write_text(json.dumps(p))
    build(str(f), str(out), NOW)
    html = out.read_text()
    for sport in ("football", "nhl"):
        sec = html[html.index(f'id="sport-{sport}"'):]
        sec = sec[:sec.index("</section>")]
        assert sec.split(">", 1)[0].count("off") == 0          # section tag itself is not hidden
        assert f'id="min-{sport}"' in sec
        assert "No games at or above" in sec
        assert '<div class="wrapt off">' in sec                # the empty table is hidden instead
    assert 'class=off' not in html.split("<section", 1)[1].split(">", 1)[0]


def test_page_script_is_valid_javascript(tmp_path):
    import re
    import shutil
    import subprocess
    import pytest
    node = shutil.which("node")
    if not node:
        pytest.skip("node not installed")
    out = tmp_path / "i.html"
    build(_fx(tmp_path), str(out), NOW)
    js = re.search(r"<script>(.*?)</script>", out.read_text(), re.S).group(1)
    f = tmp_path / "page.js"
    f.write_text(js)
    r = subprocess.run([node, "--check", str(f)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_script_tolerates_sports_that_are_not_on_the_page(tmp_path):
    """A day with no NFL has no min-nfl box; wiring listeners must skip it instead of throwing."""
    out = tmp_path / "i.html"
    build(_fx(tmp_path), str(out), NOW)
    html = out.read_text()
    assert 'id="min-nfl"' not in html
    assert "if(inputs[k])inputs[k].addEventListener" in html
