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
