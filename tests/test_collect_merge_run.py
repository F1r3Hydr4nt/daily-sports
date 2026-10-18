from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from collect.football import merge
from collect import run

DUB = ZoneInfo("Europe/Dublin")
NOW = datetime(2026, 10, 1, 16, 10, tzinfo=DUB)

def fx(h, a, t, comp="Cup"):
    return {"sport": "football", "competition": comp, "home": h, "away": a, "kickoff": t, "sources": ["fotv"]}

def pr(h, a, t, probs=None):
    return {"competition": "C", "home": h, "away": a, "kickoff": t,
            "probs": probs or {"home": 50, "draw": 25, "away": 25}}

T = datetime(2026, 10, 1, 19, 45, tzinfo=DUB)

def test_merge_attaches_predicd_to_matching_listing():
    out = merge([fx("Republic of Ireland", "Austria", T)], [pr("Ireland", "Austria", T)], NOW)
    assert len(out) == 1 and out[0]["models"][0]["source"] == "predicd.com"
    assert out[0]["kickoff"].tzinfo is not None

def test_merge_handles_women_and_diacritics():
    out = merge([fx("HB Koge Women", "Servette Women", T)], [pr("HB Køge W", "Servette FC Chênois W", T)], NOW)
    assert len(out) == 1 and out[0]["models"]

def test_merge_adds_predicd_only_fixtures_in_window():
    out = merge([], [pr("A", "B", T), pr("C", "D", NOW - timedelta(hours=3))], NOW)
    assert [(o["home"], o["away"]) for o in out] == [("A", "B")]

def test_merge_drops_finished_and_marks_live():
    live = fx("L", "M", NOW - timedelta(minutes=30))
    done = fx("X", "Y", NOW - timedelta(hours=5))
    out = {o["home"]: o for o in merge([live, done], [], NOW)}
    assert "X" not in out and out["L"]["status"] == "live"

def test_merge_drops_beyond_24h():
    assert merge([fx("A", "B", NOW + timedelta(hours=25))], [], NOW) == []

def test_merge_different_times_not_matched():
    out = merge([fx("A", "B", T)], [pr("A", "B", T + timedelta(hours=3))], NOW)
    assert len(out) == 2

def test_attach_covers_scores_and_skip_unpublished():
    games = [{"sport": "nfl", "home": "Cleveland Browns", "away": "Pittsburgh Steelers", "models": []},
             {"sport": "wnba", "home": "Las Vegas Aces", "away": "Indiana Fever", "models": []}]
    picks = {"nfl": [{"away": "Pittsburgh", "home": "Cleveland", "away_score": 18.9, "home_score": 17.59}],
             "wnba": [{"away": "Indiana", "home": "Las Vegas", "away_score": 0.0, "home_score": 0.0}]}
    notes = run.attach_covers(games, picks, fetched_at=NOW)
    assert games[0]["models"][0]["score"] == {"home": 17.59, "away": 18.9}
    assert games[1]["models"] == [] and any("wnba" in n.lower() for n in notes)

def test_fetch_failure_recorded_not_raised():
    skipped = []
    assert run.get("https://example.invalid/", skipped, fetcher=lambda u: (403, "")) is None
    assert skipped and "403" in skipped[0]
    assert run.get("u", skipped, fetcher=lambda u: (200, "ok")) == "ok"


from collect.football import align

def test_align_detects_predicd_one_hour_early():
    listings = [fx("France", "Italy", T), fx("Spain", "Czech Republic", T + timedelta(minutes=0)), fx("Belgium", "Turkey", T)]
    preds = [pr("France", "Italy", T - timedelta(hours=1)), pr("Spain", "Czech Republic", T - timedelta(hours=1)),
             pr("Belgium", "Turkey", T - timedelta(hours=1)), pr("Solo", "Match", T - timedelta(hours=1))]
    shifted, off = align(listings, preds)
    assert off == timedelta(hours=1) and shifted[3]["kickoff"] == T
    assert len(merge(listings, shifted, NOW)) == 4  # 3 matched + predicd-only Solo v Match

def test_align_no_shift_when_already_aligned():
    shifted, off = align([fx("France", "Italy", T)], [pr("France", "Italy", T)])
    assert off == timedelta(0) and shifted[0]["kickoff"] == T

def test_align_unknown_when_no_overlap():
    shifted, off = align([fx("A", "B", T)], [pr("X", "Y", T - timedelta(hours=1))])
    assert off is None and shifted[0]["kickoff"] == T - timedelta(hours=1)

def test_align_ignores_implausible_diffs():
    # same teams a week apart (e.g. a rematch) must not create a bogus offset
    shifted, off = align([fx("A", "B", T)], [pr("A", "B", T + timedelta(days=7))])
    assert off is None


def test_predicd_note_wording():
    assert run.predicd_note(timedelta(0)) is None
    assert "60 min" in run.predicd_note(timedelta(hours=1))
    assert "could not be verified" in run.predicd_note(None)


# Name variants between live-footballontv and Predicd must attach, not create duplicate rows.
import pytest

@pytest.mark.parametrize("lh,la,ph,pa", [
    ("Málaga", "Espanyol", "Málaga CF", "Espanyol Barcelona"),
    ("West Ham United", "QPR", "West Ham United", "Queens Park Rangers"),
    ("RC Lens", "Lyon", "RC Lens", "Olympique Lyon"),
    ("Preussen Munster", "Essen", "Preußen Münster", "Rot-Weiss Essen"),
    ("Avellino", "Sampdoria", "US Avellino 1912", "Sampdoria Genua"),
    ("Brest", "Angers", "Stade Brest", "Angers SCO"),
    ("Inter Milan", "Parma  (joins match in progress)", "Inter Milan", "Parma Calcio 1913"),
    ("West Brom", "Birmingham City", "West Bromwich Albion", "Birmingham City"),
])
def test_merge_attaches_name_variants_without_duplicates(lh, la, ph, pa):
    out = merge([fx(lh, la, T)], [pr(ph, pa, T)], NOW)
    assert len(out) == 1 and out[0]["models"]

def test_merge_does_not_match_youth_to_senior_or_different_clubs():
    out = merge([fx("Chelsea U18", "Fulham U18", T)], [pr("Chelsea", "Fulham", T)], NOW)
    assert len(out) == 2
    from collect.football import same_team
    assert not same_team("Manchester United", "Manchester City")

@pytest.mark.parametrize("senior,reserve", [("1. FC Köln", "1. FC Köln II"), ("Real Sociedad", "Real Sociedad B"),
                                             ("Bayern Munich", "FC Bayern Munich II")])
def test_merge_does_not_match_reserve_to_senior(senior, reserve):
    out = merge([fx(senior, "Gladbach", T)], [pr(reserve, "Gladbach", T)], NOW)
    assert len(out) == 2 and not out[0]["models"]

def test_merge_attaches_gladbach_spellings():
    out = merge([fx("FC Köln", "Borussia Mönchengladbach", T)], [pr("1. FC Köln", "Borussia M'Gladbach", T)], NOW)
    assert len(out) == 1 and out[0]["models"]


def test_merge_attaches_betis_sevilla():
    out = merge([fx("Real Betis", "FC Porto", T)], [pr("Betis Sevilla", "FC Porto", T)], NOW)
    assert len(out) == 1 and out[0]["models"]

def test_merge_truncated_listing_name_matches_when_other_team_matches():
    # live-footballontv sometimes truncates a name to its prefix ("SG"); the other team and kickoff still identify the game.
    out = merge([fx("Viktoria Köln", "SG", T)], [pr("Viktoria Köln", "Sonnenhof Großaspach", T)], NOW)
    assert len(out) == 1 and out[0]["models"]

def test_merge_truncated_name_does_not_match_unrelated_game():
    out = merge([fx("Viktoria Köln", "SG", T)], [pr("Hansa Rostock", "Sonnenhof Großaspach", T)], NOW)
    assert len(out) == 2


@pytest.mark.parametrize("lh,la,ph,pa", [
    ("Gent", "AGF Aarhus", "KAA Gent", "Aarhus GF"),
    ("Lugano", "Crvena zvezda", "FC Lugano", "Red Star Belgrade"),
    ("Marseille", "Olympiakos", "Olympique Marseille", "Olympiacos Piraeus"),
    ("Sparta Prague", "Lillestrom", "AC Sparta Praha", "Lillestrøm SK"),
    ("Hearts", "FC Nordsjaelland", "Heart of Midlothian", "FC Nordsjælland"),
])
def test_merge_one_team_plus_same_kickoff_is_the_same_game(lh, la, ph, pa):
    # a club cannot play two games at once, so one matching team at the same kickoff identifies the fixture
    out = merge([fx(lh, la, T)], [pr(ph, pa, T)], NOW)
    assert len(out) == 1 and out[0]["models"]

def test_merge_one_team_match_does_not_cross_youth_or_time():
    out = merge([fx("Chelsea", "Fulham U18", T)], [pr("Chelsea", "Fulham", T)], NOW)
    assert len(out) == 2
    out = merge([fx("Gent", "AGF Aarhus", T)], [pr("KAA Gent", "Aarhus GF", T + timedelta(minutes=25))], NOW)
    assert len(out) == 2


@pytest.mark.parametrize("men,women", [("Manchester United", "Manchester United Women"), ("Sunderland", "Sunderland AFC Women"),
                                       ("Rangers", "Rangers W")])
def test_same_team_does_not_match_men_to_women(men, women):
    from collect.football import same_team
    assert not same_team(men, women)

def test_merge_keeps_mens_and_womens_games_apart():
    out = merge([fx("Leeds United", "Manchester United", T)], [pr("Charlton Athletic Women", "Manchester United Women", T)], NOW)
    assert len(out) == 2
