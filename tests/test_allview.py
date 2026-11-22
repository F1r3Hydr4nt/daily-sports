import re
import subprocess
import shutil
import pytest
from tests.test_preview_render import fixture, page


def _two_sports():
    a = fixture(comp="Serie A")
    b = {"sport": "nhl", "competition": "NHL", "home": "Bruins", "away": "Rangers", "status": "scheduled",
         "kickoff": "2026-11-12T12:00:00+00:00", "sources": [],
         "models": [{"name": "Odds Shark", "kind": "statistical-model", "source": "oddsshark.com", "url": "https://x/",
                     "fetched_at": "2026-11-12T08:00:00+00:00", "score": {"home": 3.2, "away": 2.4}}]}
    return [a, b]


def test_view_switch_and_all_view_container_exist(tmp_path):
    html = page(tmp_path, _two_sports())
    assert 'id="view-mode"' in html and 'value="all"' in html
    assert 'id="all-view"' in html
    assert re.search(r'<section id="all-view"[^>]*class="[^"]*\boff\b', html)      # hidden until chosen


def test_sections_carry_sport_icon_and_label(tmp_path):
    html = page(tmp_path, _two_sports())
    assert 'data-icon="⚽"' in html          # football
    assert 'data-icon="\U0001F3D2"' in html      # NHL
    assert 'data-label="Football"' in html


def test_script_builds_combined_table_sorted_by_kickoff(tmp_path):
    html = page(tmp_path, _two_sports())
    js = html[html.rindex("<script>") + 8:html.rindex("</script>")]
    assert "view-mode" in js and "all-view" in js and "data-time" in js and "sporttag" in js


@pytest.mark.skipif(shutil.which("node") is None, reason="node missing")
def test_script_still_parses(tmp_path):
    html = page(tmp_path, _two_sports())
    js = html[html.rindex("<script>") + 8:html.rindex("</script>")]
    p = tmp_path / "s.js"
    p.write_text(js)
    assert subprocess.run(["node", "--check", str(p)]).returncode == 0


def test_filters_stay_reachable_in_all_view(tmp_path):
    html = page(tmp_path, _two_sports())
    assert "view-all section[data-section]>:not(h2):not(.seccontrol)" in html   # only controls stay visible
