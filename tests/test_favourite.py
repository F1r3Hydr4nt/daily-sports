import json
from datetime import datetime
from zoneinfo import ZoneInfo

from src.build import build
from src.score import favourite

NOW = datetime(2026, 11, 13, 9, 0, tzinfo=ZoneInfo("Europe/Dublin"))


def M(name="M", probs=None, score=None):
    m = {"name": name, "kind": "statistical-model", "source": "s", "url": "https://x/", "fetched_at": "2026-11-13T08:00:00+00:00"}
    if probs:
        m["probs"] = probs
    if score:
        m["score"] = score
    return m


def test_favourite_from_two_way_probabilities():
    assert favourite({"models": [M(probs={"home": 46, "away": 54})]}) == "away"      # the Hercog v Monnet case
    assert favourite({"models": [M(probs={"home": 70, "away": 30})]}) == "home"
    assert favourite({"models": [M(probs={"home": 50, "away": 50})]}) is None


def test_favourite_from_three_way_probabilities_is_the_top_outcome_and_none_for_a_draw():
    assert favourite({"models": [M(probs={"home": 20, "draw": 24, "away": 56})]}) == "away"
    assert favourite({"models": [M(probs={"home": 30, "draw": 40, "away": 30})]}) is None     # draw is the top outcome
    assert favourite({"models": [M(probs={"home": 33, "draw": 34, "away": 33})]}) is None


def test_favourite_from_a_published_score():
    assert favourite({"models": [M(score={"home": 2.9, "away": 3.4})]}) == "away"
    assert favourite({"models": [M(score={"home": 3.0, "away": 3.0})]}) is None


def test_favourite_is_none_when_models_disagree_or_there_are_none():
    f = {"models": [M("A", probs={"home": 60, "away": 40}), M("B", probs={"home": 40, "away": 60})]}
    assert favourite(f) is None
    f2 = {"models": [M("A", probs={"home": 60, "away": 40}), M("B", probs={"home": 55, "away": 45})]}
    assert favourite(f2) == "home"
    assert favourite({"models": []}) is None


def _page(tmp_path, fixtures):
    base = {"competition": "C", "kickoff": "2026-11-13T15:00:00+00:00", "status": "scheduled", "sources": []}
    p = tmp_path / "f.json"
    p.write_text(json.dumps({"fixtures": [{**base, **f} for f in fixtures], "skipped": []}))
    out = tmp_path / "i.html"
    assert build(str(p), str(out), NOW)["ok"]
    return out.read_text()


def B(name):
    return f'<strong title="Model favourite">{name}</strong>'


def _match_cell(html, name):
    i = html.index(name, html.index("<tbody>"))
    cell = html[html.rindex('<td data-label="Match">', 0, i):]
    return cell[:cell.index("</td>")]


def test_only_the_favourite_is_bold_in_the_match_cell(tmp_path):
    html = _page(tmp_path, [
        {"sport": "tennis", "home": "Polona Hercog", "away": "Carole Monnet", "models": [M("SetProb", probs={"home": 46, "away": 54})]},
        {"sport": "football", "home": "Home FC", "away": "Away FC", "models": [M("Predicd", probs={"home": 60, "draw": 25, "away": 15})]},
        {"sport": "nhl", "home": "Sharks", "away": "Islanders", "models": [M("Odds Shark", score={"home": 2.9, "away": 3.4})]},
        {"sport": "football", "home": "Even FC", "away": "Level FC", "models": [M("Predicd", probs={"home": 30, "draw": 40, "away": 30})]}])
    c = _match_cell(html, "Polona Hercog")
    assert B("Carole Monnet") in c and B("Polona Hercog") not in c
    c = _match_cell(html, "Home FC")
    assert B("Home FC") in c and B("Away FC") not in c
    c = _match_cell(html, "Sharks")
    assert B("Islanders") in c and B("Sharks") not in c
    c = _match_cell(html, "Even FC")
    assert "<strong>" not in c                                        # no favourite: nobody is bold


def test_page_explains_what_bold_means(tmp_path):
    html = _page(tmp_path, [{"sport": "tennis", "home": "A One", "away": "B Two", "models": [M("SetProb", probs={"home": 60, "away": 40})]}])
    assert "Bold = the model" in html
