import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from collect import footballontv, predicd, espn, covers

DUB = ZoneInfo("Europe/Dublin")
NOW = datetime(2026, 10, 1, 16, 10, tzinfo=DUB)

FOTV = ('<div>Thursday 1st October 2026</div>'
        '<div class="fixture"><div class="fixture__time">19:45</div><div class="fixture__teams">Republic of Ireland v Austria  </div>'
        '<div class="fixture__competition">UEFA Nations League Group Stage</div></div>'
        '<div class="fixture"><div class="fixture__time">20:00</div><div class="fixture__teams">No Opponent Listed</div>'
        '<div class="fixture__competition">X</div></div>'
        '<div>Friday 2nd October 2026</div>'
        '<div class="fixture"><div class="fixture__time">00:30</div><div class="fixture__teams">A &amp; B v C</div>'
        '<div class="fixture__competition">Cup</div></div>')

def test_footballontv_parses_days_and_skips_non_matches():
    fx = footballontv.parse(FOTV)
    assert [(f["home"], f["away"]) for f in fx] == [("Republic of Ireland", "Austria"), ("A & B", "C")]
    assert fx[0]["kickoff"] == datetime(2026, 10, 1, 19, 45, tzinfo=DUB)
    assert fx[1]["kickoff"] == datetime(2026, 10, 2, 0, 30, tzinfo=DUB)
    assert fx[0]["competition"] == "UEFA Nations League Group Stage"

PRED = ('|01.10. 19:45|-->|Ireland|-->|Austria|-|Match Info|Competition:|Nations League|2026-2027|'
        'Win Probability:|29%|28|43|Goal Probability:|1|'
        '|02.10. 02:30|-->|Seattle|-->|Kansas|-|Match Info|Competition:|MLS|Win Probability:|51%|28|21|')

def test_predicd_parse_text():
    out = predicd.parse_text(PRED, year=2026)
    assert out[0]["home"] == "Ireland" and out[0]["probs"] == {"home": 29, "draw": 28, "away": 43}
    assert out[0]["kickoff"] == datetime(2026, 10, 1, 19, 45, tzinfo=DUB)
    assert out[1]["probs"]["home"] == 51

def test_predicd_html_to_text_strips_scripts():
    t = predicd.html_to_text("<script>x=1</script><p>Hi</p><p>there</p>")
    assert "x=1" not in t and "Hi" in t

def fitt(content):
    return "<script>window['__espnfitt__']=" + json.dumps({"page": {"content": content}}) + ";</script>"

def ev(id_, away, home, date, state="pre", completed=False):
    return {"id": id_, "date": date, "completed": completed, "status": {"state": state},
            "competitors": [{"displayName": home, "isHome": True}, {"displayName": away, "isHome": False}]}

def test_espn_extract_and_us_events_filter():
    content = {"events": {"20261001": [ev("1", "Buffalo Sabres", "Columbus Blue Jackets", "2026-10-01T23:00Z"),
                                       ev("2", "Done", "Game", "2026-10-01T12:00Z", state="post", completed=True),
                                       ev("3", "Late", "Night", "2026-10-03T23:00Z")]}}
    c = espn.extract(fitt(content))
    out = espn.team_events(c, sport="nhl", label="NHL", url="u", window=(datetime(2026, 10, 1, 15, 10, tzinfo=timezone.utc), datetime(2026, 10, 2, 15, 10, tzinfo=timezone.utc)))
    assert [(o["away"], o["home"]) for o in out] == [("Buffalo Sabres", "Columbus Blue Jackets")]
    assert out[0]["status"] == "scheduled" and out[0]["kickoff"].tzinfo is not None

def test_espn_extract_missing_returns_none():
    assert espn.extract("<html>nothing</html>") is None

def test_espn_tennis_skips_finished_and_unnamed():
    comp = lambda d, st, names: {"date": d, "status": {"state": st}, "note": "Round 1",
                                 "competitors": [{"nm": n} for n in names]}
    c = {"scoreboard": {"tournaments": [{"name": "China Open", "groupings": [{"name": "Men's Singles", "competitionIds": ["1", "2", "3"]}]}],
                        "competitions": {"1": comp("2026-10-02T05:00Z", "pre", ["A", "B"]),
                                         "2": comp("2026-10-01T11:00Z", "post", ["C", "D"]),
                                         "3": comp("2026-10-02T06:00Z", "pre", ["E", None])}}}
    out = espn.tennis(c, url="u", window=(datetime(2026, 10, 1, 15, 10, tzinfo=timezone.utc), datetime(2026, 10, 2, 15, 10, tzinfo=timezone.utc)))
    assert [(o["home"], o["away"]) for o in out] == [("A", "B")]
    assert "China Open" in out[0]["competition"]

COVERS = ("|Computer Picks powered by|Odds Shark|Pittsburgh @ Cleveland|Today • 8:15 PM ET|Matchup Stats|Computer Picks|Trends|Predicted Score|PIT|PIT|⯆|18.90|@|17.59|CLE|CLE|"
          "|Indiana @ Las Vegas|Today • 1:00 PM ET|Matchup Stats|Computer Picks|Trends|Predicted Score|IND|IND|0.00|@|⯆|0.00|LV|LV|")

def test_covers_parse_scores():
    out = covers.parse_text(COVERS)
    assert out[0] == {"away": "Pittsburgh", "home": "Cleveland", "away_score": 18.9, "home_score": 17.59}

def test_covers_zero_scores_not_published():
    assert covers.parse_text(COVERS)[1]["away_score"] == 0.0
    assert all(p["away"] != "Indiana" for p in covers.published(covers.parse_text(COVERS)))

def test_covers_match_team_names():
    assert covers.same_team("N.Y. Giants", "New York Giants") and covers.same_team("Pittsburgh", "Pittsburgh Steelers")
    assert not covers.same_team("Cleveland", "Pittsburgh Steelers")


def test_every_espn_fixture_has_models_list():
    w = (datetime(2026, 10, 1, 15, 10, tzinfo=timezone.utc), datetime(2026, 10, 2, 15, 10, tzinfo=timezone.utc))
    team = espn.team_events({"events": {"d": [ev("1", "A", "B", "2026-10-01T23:00Z")]}}, "nhl", "NHL", "u", w)
    mma = espn.mma({"events": {"d": [{"date": "2026-10-02T14:00Z", "name": "PFL", "status": {"state": "pre"}}]}}, "u", w)
    golf = espn.golf({"events": [{"status": "in", "startDate": "2026-10-01T07:00Z", "endDate": "2026-10-04T07:00Z",
                                  "date": "Oct 1-4", "name": "Open", "locations": []}]}, "u", w)
    for f in team + mma + golf:
        assert f["models"] == []
