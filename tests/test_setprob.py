from datetime import datetime, timezone
from collect import setprob
from collect.run import attach_setprob

PAGE = ('<div id="ssr-matches">'
        '<div class="match-card"><div class="ssr-tourn">Stockholm</div><div class="ssr-players">Taylor Fritz vs Cameron Norrie</div>'
        '<div class="ssr-pick">Prediction: Taylor Fritz to win (75% probability)</div></div>'
        '<div class="match-card"><div class="ssr-tourn">Stockholm</div><div class="ssr-players">Borna Gojo vs Ugo Humbert</div>'
        '<div class="ssr-pick">Prediction: Ugo Humbert to win (57% probability)</div></div>'
        '<div class="match-card"><div class="ssr-tourn">Stockholm</div><div class="ssr-players">Alexander Shevchenko vs Casper Ruud</div>'
        '<div class="ssr-pick">Prediction: Casper Ruud to win (80% probability)</div></div></div>')


def test_parse_reads_players_winner_and_probability():
    out = setprob.parse(PAGE)
    assert [(p["a"], p["b"], p["winner"], p["prob"]) for p in out] == [
        ("Taylor Fritz", "Cameron Norrie", "Taylor Fritz", 75),
        ("Borna Gojo", "Ugo Humbert", "Ugo Humbert", 57),
        ("Alexander Shevchenko", "Casper Ruud", "Casper Ruud", 80)]


def test_parse_ignores_malformed_cards_and_empty_page():
    assert setprob.parse("<html>nothing</html>") == []
    bad = PAGE.replace("(75% probability)", "(n/a)")
    assert len(setprob.parse(bad)) == 2


def fx(home, away):
    return {"sport": "tennis", "home": home, "away": away, "models": []}


def test_attach_matches_by_surname_in_either_order_and_sets_two_way_probs():
    games = [fx("Cameron Norrie", "Taylor Fritz"), fx("Ugo Humbert", "Borna Gojo"),
             fx("Aleksandr Shevchenko", "Casper Ruud")]   # ESPN spells the first name differently
    at = datetime(2026, 11, 11, 9, tzinfo=timezone.utc)
    n = attach_setprob(games, setprob.parse(PAGE), at)
    assert n == 3
    m = games[0]["models"][0]
    assert m["kind"] == "statistical-model" and m["name"] == "SetProb" and m["fetched_at"] == at
    assert m["probs"] == {"home": 25, "away": 75}          # Fritz is the away player here
    assert games[1]["models"][0]["probs"] == {"home": 57, "away": 43}
    assert games[2]["models"][0]["probs"] == {"home": 20, "away": 80}


def test_attach_skips_unmatched_non_tennis_and_one_surname_only():
    games = [fx("Taylor Fritz", "Someone Else"), {"sport": "football", "home": "Taylor Fritz", "away": "Cameron Norrie", "models": []}]
    assert attach_setprob(games, setprob.parse(PAGE), datetime.now(timezone.utc)) == 0
    assert games[0]["models"] == [] and games[1]["models"] == []


def test_attach_does_not_double_attach():
    games = [fx("Taylor Fritz", "Cameron Norrie")]
    at = datetime.now(timezone.utc)
    attach_setprob(games, setprob.parse(PAGE), at)
    attach_setprob(games, setprob.parse(PAGE), at)
    assert len(games[0]["models"]) == 1


def test_accented_names_match():
    games = [fx("Alejandro Davidovich Fokina", "Zeljko Krajinovic")]
    picks = [{"a": "Alejandro Davidovich Fokina", "b": "Žeļjko Krajinović", "winner": "Alejandro Davidovich Fokina", "prob": 70, "tournament": "X"}]
    assert attach_setprob(games, picks, datetime.now(timezone.utc)) == 1


ROW = {"match_date": "2026-11-11", "tour": "wta", "tournament": "Finals - Indian Wells",
       "p1_name": "Elina Svitolina", "p2_name": "Karolina Muchova", "predicted_winner": "Elina Svitolina",
       "confidence": 57, "match_time": "2026-11-11T20:00:00+00:00", "odds_p1": 42, "odds_p2": 59, "odds_source": "kalshi"}


def test_parse_api_reads_rows_and_never_carries_odds():
    out = setprob.parse_api([ROW])
    assert out == [{"tournament": "Finals - Indian Wells", "a": "Elina Svitolina", "b": "Karolina Muchova",
                    "winner": "Elina Svitolina", "prob": 57, "time": datetime(2026, 11, 11, 20, 0, tzinfo=timezone.utc)}]
    assert not any("odds" in k for k in out[0])


def test_parse_api_skips_incomplete_rows_and_bad_input():
    bad = [dict(ROW, predicted_winner=None), dict(ROW, confidence=None), dict(ROW, predicted_winner="Someone Else"),
           dict(ROW, confidence=100), dict(ROW, match_time=None)]
    out = setprob.parse_api(bad)
    assert len(out) == 1 and out[0]["time"] is None      # only the missing match_time row survives, time unknown
    assert setprob.parse_api({"error": "Invalid parameters"}) == []
    assert setprob.parse_api(None) == []


def test_attach_time_guard_rejects_same_pair_on_another_day():
    pick = setprob.parse_api([ROW])
    near = dict(fx("Elina Svitolina", "Karolina Muchova"), kickoff=datetime(2026, 11, 11, 19, 30, tzinfo=timezone.utc))
    far = dict(fx("Elina Svitolina", "Karolina Muchova"), kickoff=datetime(2026, 11, 13, 19, 30, tzinfo=timezone.utc))
    at = datetime.now(timezone.utc)
    assert attach_setprob([near], pick, at) == 1
    assert attach_setprob([far], pick, at) == 0


def test_double_surnames_match_when_one_side_drops_a_part():
    games = [fx("Irene Burillo", "Julia Grabher")]
    pick = [{"a": "Irene Burillo Escorihuela", "b": "Julia Grabher", "winner": "Julia Grabher", "prob": 62, "tournament": "Sopo", "time": None}]
    assert attach_setprob(games, pick, datetime.now(timezone.utc)) == 1
    assert games[0]["models"][0]["probs"] == {"home": 38, "away": 62}


def test_different_players_with_a_shared_first_name_do_not_match():
    games = [fx("Irene Burillo", "Julia Grabher")]
    pick = [{"a": "Irene Smith", "b": "Julia Grabher", "winner": "Julia Grabher", "prob": 62, "tournament": "X", "time": None}]
    assert attach_setprob(games, pick, datetime.now(timezone.utc)) == 0
