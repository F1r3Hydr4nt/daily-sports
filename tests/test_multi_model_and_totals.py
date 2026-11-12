import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from collect import setprob
from collect.run import attach_setprob
from src.build import build
from src.score import win_gap

NOW = datetime(2026, 11, 12, 9, 0, tzinfo=ZoneInfo("Europe/Dublin"))
AT = datetime(2026, 11, 12, 9, 0, tzinfo=timezone.utc)


def M(name, probs=None, score=None, kind="statistical-model", **extra):
    m = {"name": name, "kind": kind, "source": f"{name.lower()}.example", "url": "https://x/",
         "fetched_at": "2026-11-12T08:00:00+00:00", **extra}
    if probs:
        m["probs"] = probs
    if score:
        m["score"] = score
    return m


def page(tmp_path, fixtures):
    base = {"competition": "C", "kickoff": "2026-11-12T15:00:00+00:00", "status": "scheduled", "sources": []}
    p = tmp_path / "f.json"
    p.write_text(json.dumps({"fixtures": [{**base, **f} for f in fixtures], "skipped": []}))
    out = tmp_path / "i.html"
    r = build(str(p), str(out), NOW)
    assert r["ok"], r
    return out.read_text()


def row(html, name):
    i = html.index(name)
    j = html.index("</tr>", i)
    return html[html.rindex("<tr", 0, i):j]


def test_two_models_both_show_with_their_numbers_and_a_disagreement_flag(tmp_path):
    html = page(tmp_path, [{"sport": "tennis", "home": "Alpha One", "away": "Beta Two", "models": [
        M("SetProb", probs={"home": 80, "away": 20}), M("OtherModel", probs={"home": 60, "away": 40})]}])
    r = row(html, "Alpha One")
    assert "SetProb (statistical-model)" in r and "OtherModel (statistical-model)" in r
    assert "home 80%" in r and "home 60%" in r
    assert "models disagree" in r and "single source" not in r


def test_score_only_models_are_listed_in_the_models_column(tmp_path):
    html = page(tmp_path, [{"sport": "nhl", "home": "Home Club", "away": "Away Club",
                            "models": [M("Odds Shark computer pick", score={"home": 3.5, "away": 2.6})]}])
    r = row(html, "Home Club")
    cell = r[r.rindex('data-label="Model predictions"'):]
    assert "Odds Shark computer pick (statistical-model)" in cell and "3.5 - 2.6" in cell
    assert "single source" in cell


def test_setprob_factor_breakdown_is_shown_for_the_favourite(tmp_path):
    factors = {"elo": [65, 35], "h2h": [67, 33], "last10": [58, 42], "surface": [54, 46]}
    html = page(tmp_path, [{"sport": "tennis", "home": "Strong Fav", "away": "Weak Dog",
                            "models": [M("SetProb", probs={"home": 63, "away": 37}, factors={"elo": 65, "h2h": 67, "last10": 58, "surface": 54})]}])
    cell = row(html, "Strong Fav")
    cell = cell[cell.rindex('data-label="Model predictions"'):]
    assert "Strong Fav" in cell and "Elo 65%" in cell and "H2H 67%" in cell and "Last 10 58%" in cell and "Surface 54%" in cell


def test_attach_orients_factors_to_the_home_player():
    row_ = {"tournament": "T", "p1_name": "Cameron Norrie", "p2_name": "Taylor Fritz", "predicted_winner": "Taylor Fritz",
            "confidence": 75, "match_time": None, "tour": "atp",
            "prob_factors": {"elo": [30, 70], "h2h": [40, 60]}}
    picks = setprob.parse_api([row_])
    games = [{"sport": "tennis", "home": "Taylor Fritz", "away": "Cameron Norrie", "models": []}]   # reversed vs SetProb
    assert attach_setprob(games, picks, AT) == 1
    assert games[0]["models"][0]["factors"] == {"elo": 70, "h2h": 60}


def test_win_gap_averages_all_two_way_models():
    f = {"models": [M("A", probs={"home": 80, "away": 20}), M("B", probs={"home": 70, "away": 30})]}
    assert win_gap(f) == 50.0                      # (60 + 40) / 2


def test_nav_and_section_show_shown_of_total_modelled(tmp_path):
    fx = [{"sport": "tennis", "home": f"P{i} Aa", "away": f"Q{i} Bb", "models": [M("SetProb", probs={"home": 90 if i == 0 else 52, "away": 10 if i == 0 else 48})]} for i in range(4)]
    html = page(tmp_path, fx)
    assert 'class="count">1 of 4<' in html                     # nav chip: 1 shown of 4 modelled (default 50-pt gap)
    sec = html[html.index('id="sport-tennis"'):]
    assert 'class="sec-count' in sec[:700] and "1 of 4 shown" in sec[:700]
    assert "Showing 1 of 4 modelled fixtures" in html
