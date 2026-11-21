from datetime import datetime, timezone

from collect import flashscore as fs

FEED = ("SA÷1¬~ZA÷EUROPE: UEFA Nations League - League C¬ZEE÷x¬~AA÷xbrNbmnd¬AD÷1794506400¬AE÷Armenia¬AF÷Cyprus¬AB÷1¬"
        "~AA÷OKNATSve¬AD÷1794513600¬AE÷England¬AF÷Croatia¬AB÷1¬"
        "~ZA÷SPAIN: Copa del Rey¬ZEE÷y¬~AA÷cup00001¬AD÷1794510000¬AE÷Tarancón¬AF÷Levante¬AB÷1¬")


def test_parse_feed_reads_matches_with_competition_and_utc_kickoff():
    ms = fs.parse_feed(FEED)
    assert [(m["id"], m["home"], m["away"], m["competition"]) for m in ms] == [
        ("xbrNbmnd", "Armenia", "Cyprus", "EUROPE: UEFA Nations League - League C"),
        ("OKNATSve", "England", "Croatia", "EUROPE: UEFA Nations League - League C"),
        ("cup00001", "Tarancón", "Levante", "SPAIN: Copa del Rey")]
    assert ms[0]["kickoff"] == datetime.fromtimestamp(1794506400, tz=timezone.utc)


def test_parse_feed_survives_garbage():
    assert fs.parse_feed("") == [] and fs.parse_feed("not a feed") == []


PREVIEW = ('<html><div id="eventPreview" class="eventPreview"><article><div class="fp-body"><p><b>A pivotal clash between '
           '<a href="/team/a/1/">Armenia</a> and <a href="/team/c/2/">Cyprus</a>.</b></p>'
           '<h2>Match News and Current Form</h2><p>Armenia have peaked early (D1, L2).</p><p>Cyprus are on the up.</p>'
           '<h2>Head-to-Head History</h2><p>Cyprus lead the series.</p>'
           '<h2>Betting Analysis</h2><p>Armenia&#x27;s inability to find the net leads us to side with the visitors, so '
           'Draw/Cyprus in the double chance market could be a worthwhile selection.</p><p>Author: Matthew Billon</p>'
           '</div></article></div><script>window.x=1</script></html>')


def test_parse_preview_splits_sections_and_author():
    p = fs.parse_preview(PREVIEW)
    assert p["intro"].startswith("A pivotal clash between Armenia and Cyprus")
    assert list(p["sections"]) == ["Match News and Current Form", "Head-to-Head History", "Betting Analysis"]
    assert "Cyprus are on the up." in p["sections"]["Match News and Current Form"]
    assert p["author"] == "Matthew Billon"
    assert "Author:" not in p["betting"] and p["betting"].startswith("Armenia's inability")


def test_parse_preview_none_when_the_page_has_no_preview():
    assert fs.parse_preview("<html><body>nothing here</body></html>") is None


def pick(text, home="Armenia", away="Cyprus"):
    return fs.parse_pick(text, home, away)


def test_double_chance_pick_covers_two_outcomes():
    p = pick("Draw/Cyprus in the double chance market could be a worthwhile selection.")
    assert p["market"] == "Double chance" and p["selection"] == "Draw/Cyprus" and set(p["covers"]) == {"draw", "away"}


def test_double_chance_codes_and_or_forms():
    assert set(pick("Armenia or Draw in the double chance market is the call.")["covers"]) == {"home", "draw"}
    assert set(pick("We like 1X double chance here.")["covers"]) == {"home", "draw"}
    assert set(pick("Double chance X2 looks fair.")["covers"]) == {"draw", "away"}


def test_win_by_handicap_pick_backs_the_team_to_win():
    p = pick("England to win by a -2 handicap could offer solid value.", "England", "Croatia")
    assert p["market"] == "Handicap -2" and p["selection"] == "England -2" and p["covers"] == ["home"]


def test_plain_team_to_win_pick():
    p = pick("Expect Cyprus to win this one.")
    assert p["market"] == "Match result" and p["selection"] == "Cyprus to win" and p["covers"] == ["away"]


def test_goals_and_btts_picks_have_a_market_but_no_outcome():
    p = pick("Over 2.5 goals looks the standout option.")
    assert p["market"] == "Over 2.5 goals" and p["covers"] is None
    q = pick("Both teams to score is worth a look.")
    assert q["market"] == "Both teams to score" and q["covers"] is None


def test_unrecognised_text_gives_no_market():
    p = pick("A tight game is expected between two evenly matched sides.")
    assert p["market"] is None and p["covers"] is None and p["text"].startswith("A tight game")


def test_pick_keeps_the_quote_short():
    assert len(pick("Cyprus to win. " + "Filler sentence. " * 80)["text"]) <= 400


def test_winning_margin_clean_sheet_and_half_time_full_time_picks_back_the_team_to_win():
    p = fs.parse_pick("home advantage makes a punt on Albania to win by a one-goal margin look viable.", "Albania", "Finland")
    assert p["market"] == "Winning margin" and p["covers"] == ["home"] and "Albania" in p["selection"]
    q = fs.parse_pick("making a Montenegro clean-sheet win an attractive option here.", "Montenegro", "Latvia")
    assert q["market"] == "Win to nil" and q["covers"] == ["home"] and q["selection"] == "Montenegro win to nil"
    r = fs.parse_pick("there appears to be safety in backing Belarus to lead at both half-time and full-time.", "San Marino", "Belarus")
    assert r["market"] == "Half-time/full-time" and r["covers"] == ["away"]


def test_handicap_still_wins_over_the_margin_rule():
    assert fs.parse_pick("England to win by a -2 handicap looks good.", "England", "Croatia")["market"] == "Handicap -2"


def test_home_or_away_win_phrase_with_a_goals_market_is_a_combined_result_pick():
    p = fs.parse_pick("With France in strong attacking form, backing an away win and over 2.5 goals could prove a worthwhile punt here.",
                      "Italy", "France")
    assert p["market"] == "Away win + Over 2.5 goals" and p["covers"] == ["away"]
    q = fs.parse_pick("A home win looks the safest route.", "Italy", "France")
    assert q["market"] == "Match result" and q["selection"] == "Italy to win" and q["covers"] == ["home"]


def test_draw_picks_alone_and_with_both_teams_to_score():
    p = fs.parse_pick("Germany have a penchant for drawing on the road in this competition and another here wouldn't be a surprise.",
                      "Serbia", "Germany")
    assert p["market"] == "Match result" and p["selection"] == "Draw" and p["covers"] == ["draw"]
    q = fs.parse_pick("with both sides still unbeaten, backing the draw and both teams to score could make sense.", "Netherlands", "Greece")
    assert q["market"] == "Draw + Both teams to score" and q["covers"] == ["draw"]


def test_backing_against_both_teams_to_score_is_the_no_market():
    p = fs.parse_pick("The form points directly to an Icelandic win, but backing against both teams to score could be an interesting alternative.",
                      "Bulgaria", "Iceland")
    assert p["market"] == "Both teams not to score" and p["covers"] is None
    q = fs.parse_pick("Both teams not to score looks likely.", "A", "B")
    assert q["market"] == "Both teams not to score"


def test_correct_score_style_pick_backs_the_team():
    p = fs.parse_pick("Given Estonia's recent defensive record and Luxembourg's struggles, a 1-0 away win could provide decent value here.",
                      "Luxembourg", "Estonia")
    assert p["market"] == "Correct score 1-0" and p["selection"] == "Estonia 1-0" and p["covers"] == ["away"]


def test_goalless_first_half_pick_has_a_market_but_no_outcome():
    p = fs.parse_pick("A bet on a goalless first half makes sense here, as a lack of goals has haunted both teams recently.", "Andorra", "Gibraltar")
    assert p["market"] == "Goalless first half" and p["covers"] is None


def test_draw_words_inside_other_markets_do_not_hijack_them():
    assert fs.parse_pick("Draw/Cyprus in the double chance market is the call.", "Armenia", "Cyprus")["market"] == "Double chance"
    assert fs.parse_pick("A draw no bet on Cyprus appeals.", "Armenia", "Cyprus")["market"] != "Match result"


def test_half_time_only_lead_is_not_a_full_time_outcome():
    p = fs.parse_pick("Based on Romania's first-half showings so far in this UNL season, backing Poland to lead at half-time looks like a good option.",
                      "Romania", "Poland")
    assert p["market"] == "Half-time lead" and p["selection"] == "Poland to lead at half-time" and p["covers"] is None
    q = fs.parse_pick("there appears to be safety in backing Belarus to lead at both half-time and full-time.", "San Marino", "Belarus")
    assert q["market"] == "Half-time/full-time" and q["covers"] == ["away"]            # unchanged


def test_win_without_conceding_and_win_and_clean_sheet_are_win_to_nil():
    a = fs.parse_pick("given Wales' struggles on the road, Norway to win without conceding looks the obvious selection here.", "Norway", "Wales")
    assert a["market"] == "Win to nil" and a["covers"] == ["home"] and a["selection"] == "Norway win to nil"
    b = fs.parse_pick("With Georgia struggling for form and goals of late, backing Hungary to win and keep a clean sheet could make sense.", "Georgia", "Hungary")
    assert b["market"] == "Win to nil" and b["covers"] == ["away"]


def test_early_goal_pick_is_a_named_market_with_no_outcome():
    p = fs.parse_pick("Given Sweden's quick starts recently, backing a home goal inside the opening 20 minutes is tempting here.", "Sweden", "Bosnia & Herzegovina")
    assert p["market"] == "Goal in first 20 minutes" and p["covers"] is None


LEAGUE_ONE = ('<div id="eventPreview"><article><p>Wigan face Barnsley in round 15. The odds bookmakers offered on this match gave Wigan a 41% win probability.</p>'
              '<h2>Current Form - Wigan</h2><p>Wigan are 21st.</p><h2>Betting Insights</h2>'
              '<p>The odds put the over 2.5 goals probability at 60%. This content was generated using AI.</p></article></div>')


def test_odds_based_betting_insights_are_not_a_writers_pick():
    p = fs.parse_preview(LEAGUE_ONE)
    assert p["betting"] == "" and "Betting Insights" in p["sections"]       # kept in the raw sections, never read as a pick
    assert p["author"] == ""


def test_handicap_names_the_backed_side_not_the_first_mentioned():
    from collect.flashscore import parse_pick
    p = parse_pick("San Marino just cannot keep the back door closed and have already crumbled against Finland once, so value may be found in backing Finland to overcome a -2 handicap.", "Finland", "San Marino")
    assert p["selection"] == "Finland -2" and p["covers"] == ["home"]


def test_half_time_full_time_double_name_pick():
    from collect.flashscore import parse_pick
    p = parse_pick("Turkey's form in this cycle and tendency to start slowly point towards France/France in the half-time/full-time market being a solid choice.", "France", "Turkey")
    assert p["market"] == "Half-time/full-time" and p["covers"] == ["home"]


def test_nov16_pick_formats():
    from collect.flashscore import parse_pick
    p = parse_pick("Despite needing a win to progress, backing what would be a sixth consecutive draw for Faroe Islands in this UNL campaign could be a shrewd selection.", "Faroe Islands", "Moldova")
    assert p["selection"] == "Draw" and p["covers"] == ["draw"]
    p = parse_pick("With Malta in good recent form and Gibraltar struggling for goals, backing the away side to win and keep a clean sheet could make sense.", "Gibraltar", "Malta")
    assert p["market"] == "Win to nil" and p["covers"] == ["away"]
    p = parse_pick("Given what is at stake, backing Iceland in the half-time/full-time market seems worth a punt.", "Iceland", "Luxembourg")
    assert p["market"] == "Half-time/full-time" and p["covers"] == ["home"]
    p = parse_pick("The H2H history suggests that backing Lithuania to win 2-0 could be an ambitious but successful pick.", "Lithuania", "Liechtenstein")
    assert p["market"] == "Correct score 2-0" and p["covers"] == ["home"]


def test_shortened_hyphenated_team_name_in_pick():
    from collect.flashscore import parse_pick
    p = parse_pick("Romania's miserable run on the road points towards a Bosnia win.", "Bosnia-Herzegovina", "Romania")
    assert p["market"] == "Match result" and p["covers"] == ["home"]


def test_shortened_ampersand_team_name_in_pick():
    from collect.flashscore import parse_pick
    p = parse_pick("Romania's run on the road points towards a Bosnia win.", "Bosnia & Herzegovina", "Romania")
    assert p["covers"] == ["home"]


def test_nov20_short_names_margin_and_clean_sheet():
    from collect.flashscore import parse_pick
    p = parse_pick("Bayern are favourites, so backing Bayern to win by 3+ goals could squeeze some value.", "Bayern Munich", "FC Köln")
    assert p["market"] == "Winning margin" and p["covers"] == ["home"] and p["selection"].endswith("3+ goals")
    p = parse_pick("The hosts' form makes backing Athletic to win with a clean sheet an alluring option.", "Athletic Bilbao", "Espanyol")
    assert p["market"] == "Win to nil" and p["covers"] == ["home"]


def test_abbreviated_flashscore_name_matches_writer_short_form():
    from collect.flashscore import parse_pick
    p = parse_pick("The hosts' form makes backing Athletic to win with a clean sheet an alluring option.", "Ath Bilbao", "Espanyol")
    assert p["market"] == "Win to nil" and p["covers"] == ["home"]


def test_nov21_compound_picks_and_roles():
    from collect.flashscore import parse_pick as P
    p = P("City’s stunning record makes backing them at a -1 handicap a route to value here.", "Manchester City", "Fulham")
    assert p["market"] == "Handicap -1" and p["covers"] == ["home"]
    p = P("making Lazio to be winning at half-time and full-time a wise choice here.", "Lazio", "Lecce")
    assert p["market"] == "Half-time/full-time" and p["covers"] == ["home"]
    p = P("backing the hosts to win and score multiple goals seems good.", "Aston Villa", "Sunderland")
    assert p["covers"] == ["home"] and p["market"].startswith("Win +")
    p = P("Tottenham to win and both teams to score is an appealing double.", "Tottenham", "Ipswich")
    assert p["market"] == "Win + Both teams to score" and p["covers"] == ["home"]
    p = P("a punt on Roma to win both halves seem appealing.", "Parma", "AS Roma")
    assert p["market"] == "Win both halves" and p["covers"] == ["away"]
    p = P("backing a Stuttgart win with a clean sheet an attractive choice.", "Schalke", "Stuttgart")
    assert p["market"] == "Win to nil" and p["covers"] == ["away"]
    p = P("backing Brest to score over 1.5 goals looks like a strong option.", "Strasbourg", "Brest")
    assert "team total" in p["market"] and p["covers"] is None
    p = P("Draw/Deportivo in the double chance market looks appealing.", "Alaves", "Dep. A Coruna")
    assert p["market"] == "Double chance" and p["covers"] == ["draw", "away"]
