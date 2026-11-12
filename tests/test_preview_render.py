import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from collect import flashscore as fs
from collect.run import attach_flashscore
from collect.synopses import apply_synopses
from src.build import build
from src.preview import predicd_top, star

NOW = datetime(2026, 11, 12, 9, 0, tzinfo=ZoneInfo("Europe/Dublin"))
AT = datetime(2026, 11, 12, 9, 0, tzinfo=timezone.utc)


def predicd(h, d, a):
    return {"name": "Predicd", "kind": "statistical-model", "source": "predicd.com", "url": "https://x/",
            "fetched_at": "2026-11-12T08:00:00+00:00", "probs": {"home": h, "draw": d, "away": a}}


def fixture(probs=(39, 28, 33), covers=("draw", "away"), market="Double chance", selection="Draw/Cyprus", synopsis=True, comp="Nations League"):
    f = {"sport": "football", "competition": comp, "home": "Armenia", "away": "Cyprus", "status": "scheduled",
         "kickoff": "2026-11-12T17:00:00+00:00", "sources": [], "models": [predicd(*probs)]}
    if covers is not False:
        pv = {"source": "flashscore.com", "match_id": "xbrNbmnd", "url": "https://www.flashscore.com/match/xbrNbmnd/",
              "fetched_at": "2026-11-12T08:00:00+00:00", "author": "Matthew Billon",
              "pick": {"market": market, "selection": selection, "covers": list(covers) if covers else None,
                       "text": "Draw/Cyprus in the double chance market could be a worthwhile selection."}}
        if synopsis:
            pv["strengths"] = {"home": "Strong at home, goals in every home game.", "away": "On a two-game winning run in the UNL."}
            pv["synopsis"] = "Armenia must win to stay in the promotion race; Cyprus arrive in better form."
        f["preview"] = pv
    return f


def page(tmp_path, fixtures):
    p = tmp_path / "f.json"
    p.write_text(json.dumps({"fixtures": fixtures, "skipped": []}))
    out = tmp_path / "i.html"
    assert build(str(p), str(out), NOW)["ok"]
    return out.read_text()


def row(html, name):
    i = html.index(name, html.index("<tbody>"))
    return html[html.rindex("<tr", 0, i):html.index("</tr>", i)]


def test_predicd_top_outcome_and_ties():
    assert predicd_top(fixture(probs=(39, 28, 33))) == "home"
    assert predicd_top(fixture(probs=(20, 24, 56))) == "away"
    assert predicd_top(fixture(probs=(40, 20, 40))) is None            # tie for first: no clear Predicd favourite
    assert predicd_top({"models": []}) is None


def test_star_when_flashscore_pick_covers_predicds_top_outcome():
    assert star(fixture(probs=(30, 28, 42), covers=("draw", "away")))          # Predicd away, pick draw/away
    assert not star(fixture(probs=(60, 20, 20), covers=("draw", "away")))      # Predicd home, pick draw/away
    assert not star(fixture(probs=(30, 28, 42), covers=None))                  # over/under or BTTS: no outcome
    assert not star(fixture(covers=False))                                     # no preview at all


def test_row_shows_a_very_apparent_star_and_the_flashscore_market(tmp_path):
    html = page(tmp_path, [fixture(probs=(30, 28, 42))])
    r = row(html, "Armenia")
    assert 'class="star"' in r and "&#9733;" in r or "★" in r
    assert "matches Predicd" in r
    assert "Flashscore pick" in r and "Double chance" in r and "Draw/Cyprus" in r


def test_no_star_but_the_pick_still_shows_when_flashscore_disagrees(tmp_path):
    r = row(page(tmp_path, [fixture(probs=(60, 20, 20))]), "Armenia")
    assert 'class="star"' not in r and "matches Predicd" not in r
    assert "Flashscore pick" in r and "Double chance" in r


def test_synopsis_strengths_link_and_attribution_are_shown(tmp_path):
    r = row(page(tmp_path, [fixture()]), "Armenia")
    assert "<details" in r and "Preview synopsis" in r
    assert "Strong at home" in r and "two-game winning run" in r and "promotion race" in r
    assert 'href="https://www.flashscore.com/match/xbrNbmnd/"' in r
    assert "Matthew Billon" in r and "summary of the flashscore preview" in r.lower()


def test_preview_without_synopsis_still_shows_pick_and_link(tmp_path):
    r = row(page(tmp_path, [fixture(synopsis=False)]), "Armenia")
    assert "Flashscore pick" in r and "flashscore.com/match/xbrNbmnd" in r and "Preview synopsis" not in r


def test_fixture_without_a_preview_is_unchanged(tmp_path):
    r = row(page(tmp_path, [fixture(covers=False)]), "Armenia")
    assert "Flashscore" not in r and 'class="star"' not in r


def test_no_odds_or_prices_are_ever_rendered(tmp_path):
    f = fixture()
    f["preview"]["pick"]["text"] = "Cyprus to win at 2.50 odds could offer value."
    r = row(page(tmp_path, [f]), "Armenia").lower()
    assert "odds" not in r and "2.50" not in r


def _feed_match(id_, home, away, ts):
    return {"id": id_, "home": home, "away": away, "competition": "EUROPE: UEFA Nations League",
            "kickoff": datetime.fromtimestamp(ts, tz=timezone.utc)}


PREVIEW_HTML = ('<div id="eventPreview"><article><p><b>Intro text.</b></p><h2>Match News and Current Form</h2><p>Form.</p>'
                '<h2>Betting Analysis</h2><p>Draw/Cyprus in the double chance market could be a worthwhile selection.</p>'
                '<p>Author: Matthew Billon</p></article></div>')


def test_attach_flashscore_matches_by_teams_and_kickoff_and_fetches_previews():
    kick = datetime(2026, 11, 12, 17, 0, tzinfo=timezone.utc)
    fx = [dict(fixture(covers=False), kickoff=kick), dict(fixture(covers=False), home="Other", away="Side", kickoff=kick),
          {"sport": "tennis", "home": "A", "away": "B", "kickoff": kick, "models": []}]
    feed = [_feed_match("xbrNbmnd", "Armenia", "Cyprus", int(kick.timestamp()) + 600)]
    fetched = []
    def fetch(url):
        fetched.append(url)
        return 200, PREVIEW_HTML
    stats, raw = attach_flashscore(fx, feed, fetch, AT)
    assert fetched == ["https://www.flashscore.com/match/xbrNbmnd/"]               # only the matched football fixture
    pv = fx[0]["preview"]
    assert pv["match_id"] == "xbrNbmnd" and pv["author"] == "Matthew Billon" and pv["pick"]["covers"] == ["draw", "away"]
    assert "preview" not in fx[1] and "preview" not in fx[2]
    assert stats == {"matched": 1, "previews": 1, "picks": 1}
    assert raw["xbrNbmnd"]["sections"]["Match News and Current Form"] == "Form." and raw["xbrNbmnd"]["home"] == "Armenia"


def test_attach_flashscore_ignores_far_kickoffs_matches_without_preview_and_failed_fetches():
    kick = datetime(2026, 11, 12, 17, 0, tzinfo=timezone.utc)
    fx = [dict(fixture(covers=False), kickoff=kick)]
    far = [_feed_match("x", "Armenia", "Cyprus", int(kick.timestamp()) + 6 * 3600)]
    assert attach_flashscore(fx, far, lambda u: (200, PREVIEW_HTML), AT)[0]["matched"] == 0
    near = [_feed_match("x", "Armenia", "Cyprus", int(kick.timestamp()))]
    stats, _ = attach_flashscore(fx, near, lambda u: (200, "<html>no preview</html>"), AT)
    assert stats == {"matched": 1, "previews": 0, "picks": 0} and "preview" not in fx[0]
    stats, _ = attach_flashscore(fx, near, lambda u: (500, ""), AT)
    assert stats["previews"] == 0


def test_apply_synopses_attaches_by_match_id_and_drops_bad_entries():
    f1 = fixture(synopsis=False)
    f2 = dict(fixture(synopsis=False))
    f2["preview"] = dict(f2["preview"], match_id="other")
    syn = {"xbrNbmnd": {"strengths": {"home": "H strong", "away": "A strong"}, "synopsis": "Short synopsis."},
           "other": {"strengths": {"home": 5}, "synopsis": ["not", "a", "string"]}, "missing": {"synopsis": "x"}}
    n = apply_synopses([f1, f2], syn)
    assert n == 1 and f1["preview"]["synopsis"] == "Short synopsis." and f1["preview"]["strengths"]["away"] == "A strong"
    assert "synopsis" not in f2["preview"]


def test_top_strip_lists_every_starred_match_even_when_the_filter_hides_the_row(tmp_path):
    starred = fixture(probs=(30, 28, 42))                       # Predicd away, pick draw/away -> star; margin < 2 so hidden by default
    plain = dict(fixture(probs=(60, 20, 20)), home="Other One", away="Other Two")
    html = page(tmp_path, [starred, plain])
    strip = html[html.index('class="starstrip"'):]
    strip = strip[:strip.index("</div>")]
    assert "Armenia v Cyprus" in strip and "Other One" not in strip
    assert "Double chance" in strip and "1 " in strip
    assert 'class="off"' in row(html, "Armenia")[:200] or "off" in row(html, "Armenia")[:200]     # the row itself is filtered out


def test_no_strip_when_nothing_is_starred(tmp_path):
    assert 'class="starstrip"' not in page(tmp_path, [fixture(probs=(60, 20, 20))])


def test_strip_does_not_repeat_the_market_when_there_is_no_separate_selection(tmp_path):
    f = fixture(probs=(30, 28, 42), market="Away win + Over 2.5 goals", selection="", covers=("away",))
    strip = page(tmp_path, [f])
    strip = strip[strip.index('class="starstrip"'):]
    strip = strip[:strip.index("</div>")]
    assert strip.count("Away win + Over 2.5 goals") == 1
