import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from src.build import build
from src.cups import is_cup

NOW = datetime(2026, 11, 12, 9, 0, tzinfo=ZoneInfo("Europe/Dublin"))


@pytest.mark.parametrize("name", ["Copa del Rey", "FA Cup First Round", "Carabao Cup", "DFB-Pokal", "KNVB Cup",
                                  "Coupe de France", "Coppa Italia", "EFL Trophy", "Taça de Portugal", "Scottish League Cup",
                                  "Women's FA Cup", "Copa Paraiba", "Super Cup", "Supercopa de España", "KNVB Beker"])
def test_domestic_cups_are_cups(name):
    assert is_cup(name)


@pytest.mark.parametrize("name", ["Premier League", "Segunda División", "Champions League", "Women's Champions League League Phase",
                                  "Europa League", "Conference League", "UEFA Nations League", "World Cup Qualifiers",
                                  "Africa Cup of Nations - Qualification", "Friendlies", "Copa Libertadores", "", None,
                                  "Bundesliga 2", "Cupertino Premier"])
def test_leagues_and_international_tournaments_are_not_cups(name):
    assert not is_cup(name)


def _m(probs):
    return {"name": "Predicd", "kind": "statistical-model", "source": "predicd.com", "url": "https://x/",
            "fetched_at": "2026-11-12T08:00:00+00:00", "probs": probs}


def _page(tmp_path, comps):
    base = {"sport": "football", "kickoff": "2026-11-12T19:00:00+00:00", "status": "scheduled", "sources": []}
    fx = [{**base, "home": f"Home{i} FC", "away": f"Away{i} FC", "competition": c,
           "models": [_m({"home": 85 - i, "draw": 10, "away": 5 + i})]} for i, c in enumerate(comps)]
    p = tmp_path / "f.json"
    p.write_text(json.dumps({"fixtures": fx, "skipped": []}))
    out = tmp_path / "i.html"
    assert build(str(p), str(out), NOW)["ok"]
    return out.read_text()


def test_cup_games_go_in_a_closed_accordion_with_their_own_table(tmp_path):
    html = _page(tmp_path, ["Segunda División", "Copa del Rey", "FA Cup First Round"])
    sec = html[html.index('id="sport-football"'):html.index("</section>", html.index('id="sport-football"'))]
    main = sec[:sec.index('<details class="cups"')]
    cups = sec[sec.index('<details class="cups"'):]
    assert "Home0 FC" in main and "Home1 FC" not in main and "Home2 FC" not in main
    assert "Home1 FC" in cups and "Home2 FC" in cups and "Home0 FC" not in cups
    assert "<details class=\"cups\" open" not in sec and 'class="cups" open' not in sec      # closed by default
    assert "Cup games" in cups and "2 of 2 shown" in cups.split("</summary>")[0]
    assert "rotate" in cups.split("</summary>")[0].lower()                                   # the caution about cup ties
    assert cups.count("<table>") == 1


def test_no_accordion_when_there_are_no_cup_games(tmp_path):
    html = _page(tmp_path, ["Segunda División", "Premier League"])
    assert 'class="cups"' not in html


def test_cup_rows_obey_the_same_football_margin_filter_and_count_in_the_nav(tmp_path):
    html = _page(tmp_path, ["Premier League", "Copa del Rey"])
    i = html.index("Home1 FC")
    row = html[html.rindex("<tr", 0, i):i]
    assert 'data-sport="football"' in row and "data-margin=" in row
    assert 'class="count">2 of 2<' in html


def test_script_handles_more_than_one_table_per_section(tmp_path):
    html = _page(tmp_path, ["Premier League", "Copa del Rey"])
    js = html[html.rindex("<script>"):]
    assert "querySelectorAll('tbody')" in js and "cup-count" in js


def test_open_accordion_explains_when_the_filter_hides_every_cup_game(tmp_path):
    html = _page(tmp_path, ["Premier League", "Copa del Rey"])      # Home1: 84% fav, margin >= 2 -> shown
    html2 = _page(tmp_path, ["Premier League", "Copa del Rey"])
    cups = html2[html2.index('<details class="cups"'):]
    assert 'class="cup-empty muted' in cups                      # message exists, hidden while rows are visible
    assert "cup-empty" in html2[html2.rindex("<script>"):]       # script toggles it


def test_accordion_chevron_css_escape_survives_python_string_handling(tmp_path):
    html = _page(tmp_path, ["Premier League", "Copa del Rey"])
    assert 'content:"\\25B8"' in html          # a literal backslash escape, not an octal control character
    assert "\x15" not in html
