import json
from src.country import competition_flag, competition_html
from src.window import to_dublin  # noqa: F401

ENG, SCO, WAL = "gb-eng", "gb-sct", "gb-wls"


def test_domestic_leagues_get_their_country_flag():
    assert competition_flag("Serie A") == "it"
    assert competition_flag("Ligue 1") == "fr"
    assert competition_flag("Eredivisie") == "nl"
    assert competition_flag("Championship") == ENG
    assert competition_flag("Scottish Premiership") == SCO
    assert competition_flag("Cymru Premier") == WAL
    assert competition_flag("Série A") == "br"


def test_stage_suffix_and_women_and_cups_use_the_same_country():
    assert competition_flag("Copa del Rey\xa0Round of 32") == "es"
    assert competition_flag("Women's Super League") == ENG
    assert competition_flag("Frauen Bundesliga") == "de"
    assert competition_flag("FA Cup\xa0First Round") == ENG


def test_continental_and_international_get_confederation_marks():
    assert competition_flag("UEFA Champions League\xa0League Phase") == "eu"
    assert competition_flag("UEFA Nations League\xa0Group Stage") == "eu"
    assert competition_flag("AFC Champions League Elite") == "world"
    assert competition_flag("CONCACAF Nations League") == "world"
    assert competition_flag("FIFA U17 World Cup") == "world"


def test_ambiguous_or_unknown_names_get_no_flag():
    assert competition_flag("Super League") == ""
    assert competition_flag("Superliga") == ""
    assert competition_flag("Liga 1") == ""
    assert competition_flag("Some Unknown Trophy") == ""
    assert competition_flag(None) == ""


def test_html_has_flag_with_country_title_and_escapes_name():
    h = competition_html("Serie A <b>")
    assert "it" in h and 'title="Italy"' in h and "&lt;b&gt;" in h
    assert competition_html("Mystery League") == "Mystery League"


def test_page_shows_flag_for_football_row_only(tmp_path):
    from tests.test_preview_render import fixture, page
    html = page(tmp_path, [fixture(comp="Serie A")])
    assert "it" in html and 'title="Italy"' in html


def test_brazilian_serie_a_is_not_italian():
    assert competition_flag("Campeonato Brasileiro Serie A") == "br"
    assert competition_flag("Série A") == "br"
    assert competition_flag("Serie A") == "it"


def test_every_mapped_code_has_an_image_file():
    from src.country import _RULES, FLAG_DIR
    for _rx, code, _name in _RULES:
        assert (FLAG_DIR / f"{code}.svg").exists(), code


def test_only_used_flags_are_embedded():
    from src.country import flag_css
    css = flag_css({"it"})
    assert ".fl-it{" in css and ".fl-fr{" not in css
