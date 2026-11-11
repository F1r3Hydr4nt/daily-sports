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
