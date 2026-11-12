import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from collect import setprob
from collect.run import attach_setprob, setprob_only_fixtures
from src.build import build
from src.score import win_gap

NOW = datetime(2026, 11, 11, 9, 0, tzinfo=ZoneInfo("Europe/Dublin"))
UTC = timezone.utc
WIN = (NOW.astimezone(UTC), NOW.astimezone(UTC) + timedelta(hours=24))
AT = datetime(2026, 11, 11, 9, 0, tzinfo=UTC)


def row(a, b, winner, conf, tour="atp-challenger", when="2026-11-11T15:00:00+00:00", tourn="Orleans"):
    return {"tournament": tourn, "p1_name": a, "p2_name": b, "predicted_winner": winner, "confidence": conf,
            "match_time": when, "tour": tour, "odds_p1": 40, "odds_p2": 60}


def test_win_gap_is_percentage_point_difference_for_two_way_models():
    m = {"name": "SetProb", "kind": "statistical-model", "source": "s", "url": "u", "fetched_at": AT,
         "probs": {"home": 20, "away": 80}}
    assert win_gap({"sport": "tennis", "models": [m]}) == 60
    assert win_gap({"sport": "tennis", "models": []}) is None
    three = dict(m, probs={"home": 50, "draw": 25, "away": 25})
    assert win_gap({"sport": "football", "models": [three]}) is None   # football keeps its goal margin


def test_parse_api_keeps_the_tour():
    assert setprob.parse_api([row("A B", "C D", "A B", 60)])[0]["tour"] == "atp-challenger"


def test_attach_marks_matched_picks_used():
    games = [{"sport": "tennis", "home": "A Bee", "away": "C Dee", "models": []}]
    picks = setprob.parse_api([row("A Bee", "C Dee", "A Bee", 60), row("E Eff", "G Gee", "E Eff", 70)])
    attach_setprob(games, picks, AT)
    assert [p.get("used") for p in picks] == [True, None]


def test_unmatched_picks_become_setprob_sourced_fixtures_inside_the_window():
    picks = setprob.parse_api([
        row("Benjamin Bonzi", "Tom Gentzsch", "Benjamin Bonzi", 66),
        row("Late Player", "Other Late", "Late Player", 60, when="2026-11-13T15:00:00+00:00"),   # outside 24h
        row("Gone Player", "Other Gone", "Gone Player", 60, when="2026-11-11T02:00:00+00:00")])  # long finished
    out = setprob_only_fixtures(picks, [], WIN, AT)
    assert len(out) == 1
    f = out[0]
    assert (f["sport"], f["home"], f["away"], f["status"]) == ("tennis", "Benjamin Bonzi", "Tom Gentzsch", "scheduled")
    assert f["competition"] == "ATP Challenger - Orleans" and f["kickoff"] == datetime(2026, 11, 11, 15, 0, tzinfo=UTC)
    assert f["sources"] == [setprob.URL]
    m = f["models"][0]
    assert m["name"] == "SetProb" and m["probs"] == {"home": 66, "away": 34} and m["fetched_at"] == AT


def test_no_duplicate_when_espn_already_lists_the_match_under_a_variant_name():
    espn = [{"sport": "tennis", "home": "Benjamin Bonzi", "away": "Gentzsch", "models": [],
             "kickoff": datetime(2026, 11, 11, 15, 30, tzinfo=UTC)}]
    picks = setprob.parse_api([row("Benjamin Bonzi", "Tom Gentzsch", "Benjamin Bonzi", 66)])
    assert setprob_only_fixtures(picks, espn, WIN, AT) == []


def test_used_picks_are_not_added_again():
    picks = setprob.parse_api([row("A Bee", "C Dee", "A Bee", 60)])
    picks[0]["used"] = True
    assert setprob_only_fixtures(picks, [], WIN, AT) == []


def _page(tmp_path):
    m = lambda p: {"name": "SetProb", "kind": "statistical-model", "source": "setprobability.pages.dev",
                   "url": "https://x/", "fetched_at": "2026-11-11T08:00:00+00:00", "probs": p}
    base = {"sport": "tennis", "competition": "C", "kickoff": "2026-11-11T15:00:00+00:00", "status": "scheduled", "sources": []}
    fx = [{**base, "home": "Strong Fav", "away": "Weak Dog", "models": [m({"home": 85, "away": 15})]},
          {**base, "home": "Even One", "away": "Even Two", "models": [m({"home": 52, "away": 48})]}]
    p = tmp_path / "f.json"
    p.write_text(json.dumps({"fixtures": fx, "skipped": []}))
    out = tmp_path / "i.html"
    r = build(str(p), str(out), NOW)
    return r, out.read_text()


def _row_html(html, name):
    i = html.index(name)
    return html[html.rindex("<tr", 0, i):i]


def test_tennis_has_a_gap_filter_defaulting_to_50_points(tmp_path):
    r, html = _page(tmp_path)
    assert r["ok"], r
    assert 'id="min-tennis"' in html and 'value="50"' in html and "percentage points" in html
    assert 'data-margin="70.00"' in _row_html(html, "Strong Fav")
    assert 'class="off"' not in _row_html(html, "Strong Fav")          # 70 >= 50 shown
    assert 'class="off"' in _row_html(html, "Even One")                # 4 < 50 hidden by default, still in the HTML
    assert "tennis:document.getElementById('min-tennis')" in html


def test_tennis_row_shows_favourite_and_gap_in_the_score_column(tmp_path):
    _, html = _page(tmp_path)
    row = html[html.index("Strong Fav"):html.index("Even One")]
    assert "85%" in row and "gap 70" in row and "Strong Fav" in row
    assert "win probability" in row and "no score" in row.lower()


def test_tennis_filter_is_a_slider_linked_to_the_number_box(tmp_path):
    _, html = _page(tmp_path)
    assert 'id="min-tennis-slider"' in html and 'type="range"' in html
    sl = html[html.index('id="min-tennis-slider"'):]
    sl = sl[:sl.index(">")]
    assert 'min="0"' in sl and 'max="100"' in sl and 'value="50"' in sl
    assert html.index('id="min-tennis-slider"') < html.index("<table>", html.index('id="sport-tennis"'))   # above the table
    assert "min-tennis-slider" in html[html.index("<script>"):]                                        # script keeps them in sync


def test_page_carries_the_layout_v4_stamp(tmp_path):
    _, html = _page(tmp_path)
    assert "Layout v5" in html
