import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from src.build import build
from src.gender import is_female

NOW = datetime(2026, 11, 13, 9, 0, tzinfo=ZoneInfo("Europe/Dublin"))


def fx(sport="football", comp="", home="A", away="B"):
    return {"sport": sport, "competition": comp, "home": home, "away": away}


@pytest.mark.parametrize("f", [
    fx("football", "A-League Women", "Adelaide United Women", "Wellington Phoenix Women"),
    fx("football", "DFB Pokal Frauen\xa0Round of 16", "Bayern Munich Women", "Bayer Leverkusen Women"),
    fx("football", "FIFA U17 Women's World Cup\xa0Final", "Japan Women U17", "Nigeria Women U17"),
    fx("football", "Women's Champions League League Phase", "Barcelona Women", "Arsenal Women"),
    fx("football", "Nations League", "Benfica Lisbon W", "Austria Vienna W"),                  # no gender word in the competition
    fx("football", "Liga F", "Real Madrid", "Barcelona"),
    fx("football", "Division 1 Féminine", "Lyon", "PSG"),
    fx("tennis", "Angola Ladies Open - Women's Singles Final - Lwena Court", "Anna Blinkova", "Sofya Lansere"),
    fx("tennis", "WTA Challenger - Sopo", "Polona Hercog", "Carole Monnet"),
    fx("tennis", "WTA - Finals - Indian Wells", "Aryna Sabalenka", "Elina Svitolina"),
    fx("ncaa", "NCAA Women's Basketball", "Akron Zips", "South Alabama Jaguars"),
    fx("wnba", "WNBA", "Aces", "Liberty"),
    fx("golf", "LPGA Tour Championship"),
    fx("rugby", "Women's Six Nations", "England", "France"),
    fx("tennis", "ITF W35 Pune - Singles Round 1", "A One", "B Two"),
    fx("tennis", "W75 Santiago", "A One", "B Two"),
])
def test_womens_fixtures_are_detected(f):
    assert is_female(f)


@pytest.mark.parametrize("f", [
    fx("football", "Premier League", "Arsenal", "Chelsea"),
    fx("football", "UEFA Nations League Group Stage", "England", "Croatia"),
    fx("tennis", "Bybit Stockholm Open - Men's Singles Round 2", "Taylor Fritz", "Cameron Norrie"),
    fx("tennis", "ATP Challenger - Orleans", "Benjamin Bonzi", "Tom Gentzsch"),
    fx("tennis", "ITF M25 Monastir", "A One", "B Two"),
    fx("ncaa", "NCAA Men's Basketball", "Alabama A&M Bulldogs", "Mississippi U for Women Owls"),     # opponent's name says Women
    fx("ncaa", "NCAA Men's Basketball", "Lamar Cardinals", "Centenary (LA) Ladies"),
    fx("ncaa", "NCAA Football", "Pittsburgh Panthers", "Florida State Seminoles"),
    fx("nhl", "NHL", "Sharks", "Islanders"),
    fx("football", "", "Wolverhampton Wanderers", "Wigan Athletic"),
    fx("football", "Segunda División", "Sabadell", "Real Sociedad B"),
])
def test_mens_and_open_fixtures_are_not_flagged(f):
    assert not is_female(f)


def M(probs):
    return {"name": "Predicd", "kind": "statistical-model", "source": "predicd.com", "url": "https://x/",
            "fetched_at": "2026-11-13T08:00:00+00:00", "probs": probs}


def page(tmp_path, fixtures):
    base = {"kickoff": "2026-11-13T19:00:00+00:00", "status": "scheduled", "sources": []}
    p = tmp_path / "f.json"
    p.write_text(json.dumps({"fixtures": [{**base, **f} for f in fixtures], "skipped": []}))
    out = tmp_path / "i.html"
    assert build(str(p), str(out), NOW)["ok"]
    return out.read_text()


def sec(html, sport):
    i = html.index(f'id="sport-{sport}"')
    return html[i:html.index("</section>", i)]


def test_womens_fixtures_sit_in_a_closed_accordion_at_the_bottom_of_the_section(tmp_path):
    three = lambda h: M({"home": h, "draw": 10, "away": 90 - h})
    html = page(tmp_path, [
        {"sport": "football", "competition": "Premier League", "home": "Mens One", "away": "Mens Two", "models": [three(80)]},
        {"sport": "football", "competition": "Copa del Rey", "home": "Cup One", "away": "Cup Two", "models": [three(80)]},
        {"sport": "football", "competition": "A-League Women", "home": "Fem One Women", "away": "Fem Two Women", "models": [three(80)]},
        {"sport": "football", "competition": "DFB Pokal Frauen", "home": "Fem Cup Women", "away": "Fem Cup Two Women", "models": [three(80)]}])
    s = sec(html, "football")
    main = s[:s.index('<details class="acc cups"')]
    cups = s[s.index('<details class="acc cups"'):s.index('<details class="acc womens"')]
    fem = s[s.index('<details class="acc womens"'):]
    assert "Mens One" in main and "Fem One" not in main and "Cup One" not in main
    assert "Cup One" in cups and "Fem Cup" not in cups                  # a women's cup goes to the women's accordion only
    assert "Fem One" in fem and "Fem Cup" in fem and "Mens One" not in fem
    assert s.index('class="acc cups"') < s.index('class="acc womens"')   # women's last, at the bottom
    assert "open" not in s[s.index('<details class="acc womens"'):s.index(">", s.index('<details class="acc womens"'))]
    head = fem.split("</summary>")[0]
    assert "Women" in head and "2 of 2 shown" in head and "reveal" in head.lower()
    assert fem.count("<table>") == 1


def test_whole_womens_sections_such_as_wnba_are_just_the_accordion(tmp_path):
    html = page(tmp_path, [{"sport": "wnba", "competition": "WNBA", "home": "Aces", "away": "Liberty",
                            "models": [M({"home": 55, "away": 45})]}])
    s = sec(html, "wnba")
    assert 'class="acc womens"' in s and s.count("<table>") == 1
    assert "Aces" in s[s.index('<details class="acc womens"'):]


def test_gender_split_applies_to_tennis_and_guards_against_name_false_positives(tmp_path):
    two = lambda h: M({"home": h, "away": 100 - h})
    html = page(tmp_path, [
        {"sport": "tennis", "competition": "WTA Challenger - Sopo", "home": "Polona Hercog", "away": "Carole Monnet", "models": [two(30)]},
        {"sport": "tennis", "competition": "ATP Challenger - Orleans", "home": "Benjamin Bonzi", "away": "Tom Gentzsch", "models": [two(80)]},
        {"sport": "ncaa", "competition": "NCAA Men's Basketball", "home": "Alabama A&M", "away": "Mississippi U for Women Owls", "models": [two(70)]}])
    t = sec(html, "tennis")
    assert "Polona Hercog" in t[t.index('class="acc womens"'):] and "Polona Hercog" not in t[:t.index('class="acc womens"')]
    assert "Benjamin Bonzi" in t[:t.index('class="acc womens"')]
    n = sec(html, "ncaa")
    assert 'class="acc womens"' not in n and "Mississippi U for Women Owls" in n


def test_no_womens_accordion_when_there_are_none(tmp_path):
    html = page(tmp_path, [{"sport": "football", "competition": "Premier League", "home": "A One", "away": "B Two",
                            "models": [M({"home": 60, "draw": 20, "away": 20})]}])
    assert 'class="acc womens"' not in html


def test_star_strip_leaves_out_women_and_says_how_many(tmp_path):
    def f(home, away, comp):
        return {"sport": "football", "competition": comp, "home": home, "away": away, "models": [M({"home": 20, "draw": 24, "away": 56})],
                "preview": {"source": "flashscore.com", "match_id": home, "url": "https://www.flashscore.com/match/x/", "fetched_at": "2026-11-13T08:00:00+00:00",
                            "author": "A", "pick": {"market": "Match result", "selection": f"{away} to win", "covers": ["away"], "text": "x"}}}
    html = page(tmp_path, [f("Mens One", "Mens Two", "Premier League"), f("Fem One Women", "Fem Two Women", "A-League Women")])
    strip = html[html.index('class="starstrip"'):]
    strip = strip[:strip.index("</div>")]
    assert "Mens One" in strip and "Fem One" not in strip
    assert "1 more starred" in strip and "women" in strip.lower()
