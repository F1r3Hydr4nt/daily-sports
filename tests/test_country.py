import json
from src.country import competition_flag, competition_html
from src.window import to_dublin  # noqa: F401

ENG, SCO, WAL = "\U0001F3F4\U000E0067\U000E0062\U000E0065\U000E006E\U000E0067\U000E007F", "\U0001F3F4\U000E0067\U000E0062\U000E0073\U000E0063\U000E0074\U000E007F", "\U0001F3F4\U000E0067\U000E0062\U000E0077\U000E006C\U000E0073\U000E007F"


def test_domestic_leagues_get_their_country_flag():
    assert competition_flag("Serie A") == "\U0001F1EE\U0001F1F9"
    assert competition_flag("Ligue 1") == "\U0001F1EB\U0001F1F7"
    assert competition_flag("Eredivisie") == "\U0001F1F3\U0001F1F1"
    assert competition_flag("Championship") == ENG
    assert competition_flag("Scottish Premiership") == SCO
    assert competition_flag("Cymru Premier") == WAL
    assert competition_flag("Série A") == "\U0001F1E7\U0001F1F7"


def test_stage_suffix_and_women_and_cups_use_the_same_country():
    assert competition_flag("Copa del Rey\xa0Round of 32") == "\U0001F1EA\U0001F1F8"
    assert competition_flag("Women's Super League") == ENG
    assert competition_flag("Frauen Bundesliga") == "\U0001F1E9\U0001F1EA"
    assert competition_flag("FA Cup\xa0First Round") == ENG


def test_continental_and_international_get_confederation_marks():
    assert competition_flag("UEFA Champions League\xa0League Phase") == "\U0001F1EA\U0001F1FA"
    assert competition_flag("UEFA Nations League\xa0Group Stage") == "\U0001F1EA\U0001F1FA"
    assert competition_flag("AFC Champions League Elite") == "\U0001F30F"
    assert competition_flag("CONCACAF Nations League") == "\U0001F30E"
    assert competition_flag("FIFA U17 World Cup") == "\U0001F30D"


def test_ambiguous_or_unknown_names_get_no_flag():
    assert competition_flag("Super League") == ""
    assert competition_flag("Superliga") == ""
    assert competition_flag("Liga 1") == ""
    assert competition_flag("Some Unknown Trophy") == ""
    assert competition_flag(None) == ""


def test_html_has_flag_with_country_title_and_escapes_name():
    h = competition_html("Serie A <b>")
    assert "\U0001F1EE\U0001F1F9" in h and 'title="Italy"' in h and "&lt;b&gt;" in h
    assert competition_html("Mystery League") == "Mystery League"


def test_page_shows_flag_for_football_row_only(tmp_path):
    from tests.test_preview_render import fixture, page
    html = page(tmp_path, [fixture(comp="Serie A")])
    assert "\U0001F1EE\U0001F1F9" in html and 'title="Italy"' in html


def test_brazilian_serie_a_is_not_italian():
    assert competition_flag("Campeonato Brasileiro Serie A") == "\U0001F1E7\U0001F1F7"
    assert competition_flag("Série A") == "\U0001F1E7\U0001F1F7"
    assert competition_flag("Serie A") == "\U0001F1EE\U0001F1F9"
