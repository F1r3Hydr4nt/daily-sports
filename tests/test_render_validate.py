from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from src.render import render
from src.validate import check, reject_stale

DUB = ZoneInfo("Europe/Dublin")
NOW = datetime(2026, 10, 1, 9, 0, tzinfo=DUB)

def fixture(sport="football", home="Home FC", away="Away FC", probs=((60, 40), (50, 50))):
    models = [{"name": f"m{i}", "kind": "statistical-model", "source": "predicd", "url": "https://predicd.com",
               "fetched_at": NOW, "probs": {"home": p[0], "away": p[1]}} for i, p in enumerate(probs)]
    return {"sport": sport, "competition": "Cup", "home": home, "away": away,
            "kickoff": datetime(2026, 10, 1, 18, 0, tzinfo=timezone.utc), "status": "scheduled",
            "models": models, "sources": ["feed"]}

def page(fx, skipped=None):
    return render(fx, now=NOW, skipped=skipped or [])

def test_only_sports_with_events_have_tables():
    h = page([fixture()])
    assert "Football" in h and "Tennis" not in h

def test_irish_time_shown():
    assert "19:00" in page([fixture()])  # 18:00 UTC in summer = 19:00 IST

def test_required_page_features():
    h = page([fixture()])
    for s in ("prefers-color-scheme: dark", 'name="viewport"', "gamble responsibly", "Sources", "Europe/Dublin"):
        assert s in h

def test_no_odds_columns():
    h = page([fixture()]).lower()
    assert "paddy" not in h and "bookmaker %" not in h

def test_disagreement_flag_and_aria_bars():
    h = page([fixture(probs=((70, 30), (50, 50)))])
    assert "flag" in h and 'aria-label="' in h

def test_html_escaped():
    assert "<script>x" not in page([fixture(home="<script>x")])

def test_skipped_sources_listed():
    assert "stale page" in page([fixture()], skipped=["covers.com: stale page"])

def test_no_external_urls_in_resources():
    h = page([fixture()])
    assert "src=\"http" not in h and "href=\"http://" not in h and "<link" not in h

def test_quality_gate_empty_and_out_of_window():
    from src.window import Window
    w = Window.from_now(NOW)
    assert not check([], w)["ok"]
    old = fixture(); old["kickoff"] = datetime(2026, 9, 1, tzinfo=timezone.utc)
    assert any("outside" in e for e in check([old], w)["errors"])
    assert check([fixture()], w)["ok"]

def test_banner_when_gate_fails():
    assert "WARNING" in render([], now=NOW, skipped=[], errors=["no fixtures"])

def test_reject_stale_model_page():
    feed = [fixture(home="A", away="B")]
    page_fx = [fixture(home="X", away="Y")]
    ok, reason = reject_stale(feed, page_fx, min_match=0.5)
    assert not ok and reason
    ok, _ = reject_stale(feed, [fixture(home="A", away="B")], min_match=0.5)
    assert ok


def test_score_model_rendered_and_not_flagged():
    f = fixture(probs=())
    f["models"] = [{"name": "Odds Shark", "kind": "statistical-model", "source": "covers.com", "url": "u",
                    "fetched_at": NOW, "score": {"home": 17.59, "away": 18.9}}]
    h = page([f])
    assert "predicted score" in h.lower() and "17.6" in h and "18.9" in h
    assert 'class="flag"' not in h and "single source" not in h


def test_next_day_kickoff_shows_date_label():
    f = fixture()
    f["kickoff"] = datetime(2026, 10, 1, 23, 30, tzinfo=timezone.utc)  # 00:30 IST on 2 Oct
    h = page([f])
    assert "00:30" in h and "Fri 02 Oct" in h

def test_same_day_kickoff_has_no_date_label():
    assert "Thu 01 Oct 19:00" not in page([fixture()])

def test_mobile_stacking_css_present():
    assert "max-width" in page([fixture()]) and "data-label" in page([fixture()])


def test_artifact_fragment_strips_document_wrapper():
    from src.render import artifact_fragment
    frag = artifact_fragment(page([fixture()]))
    low = frag.lower()
    for bad in ("<!doctype", "<html", "<head", "<body", "</body", 'name="viewport"'):
        assert bad not in low
    assert "<title>" in low and "<style>" in low and "Home FC" in frag
    assert low.index("<title>") < 8000


def two_sports():
    return [fixture(sport="football"), fixture(sport="tennis", home="P1", away="P2", probs=((55, 45),))]

def test_jump_nav_lists_only_sports_with_events_with_counts():
    h = page(two_sports())
    assert 'href="#sport-football"' in h and 'href="#sport-tennis"' in h and 'href="#sport-golf"' not in h
    assert 'id="sport-football"' in h and 'id="sport-tennis"' in h
    assert '<nav' in h and 'class="count">1<' in h

def test_three_way_bar_has_distinct_segment_classes_and_legend():
    f = fixture()
    f["models"] = [{"name": "m", "kind": "statistical-model", "source": "s", "url": "u", "fetched_at": NOW,
                    "probs": {"home": 50, "draw": 30, "away": 20}}]
    h = page([f])
    assert 'class="seg home"' in h and 'class="seg draw"' in h and 'class="seg away"' in h
    assert "legend" in h

def test_two_way_bar_has_no_draw_segment():
    h = page([fixture(probs=((60, 40),))])
    assert 'class="seg home"' in h and 'class="seg away"' in h and 'class="seg draw"' not in h

def test_coverage_notes_box_near_top_when_skipped():
    h = page([fixture()], skipped=["cricket: blocked"])
    assert h.index("Coverage notes") < h.index('<h2 class="sport"')
    assert "cricket: blocked" in h

def test_summary_counts_in_header():
    h = page(two_sports())
    assert "2 fixtures" in h and "2 sports" in h
