from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from src.window import Window, to_dublin

DUB = ZoneInfo("Europe/Dublin")

def test_window_is_24h_from_now():
    now = datetime(2026, 10, 1, 9, 0, tzinfo=DUB)
    w = Window.from_now(now)
    assert w.start == now and w.end == now + timedelta(hours=24)

def test_utc_summer_to_irish_time():
    assert to_dublin(datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc)).strftime("%H:%M") == "11:00"

def test_utc_winter_equals_irish_time():
    assert to_dublin(datetime(2026, 12, 1, 10, 0, tzinfo=timezone.utc)).strftime("%H:%M") == "10:00"

def test_dst_end_window_is_24h_elapsed():
    now = datetime(2026, 10, 24, 9, 0, tzinfo=DUB)  # clocks go back 25 Oct 2026
    w = Window.from_now(now)
    assert (w.end.astimezone(timezone.utc) - w.start.astimezone(timezone.utc)) == timedelta(hours=24)
    assert w.end.strftime("%H:%M") == "08:00"

def test_naive_now_rejected():
    import pytest
    with pytest.raises(ValueError):
        Window.from_now(datetime(2026, 10, 1, 9, 0))

def test_contains_boundaries():
    now = datetime(2026, 10, 1, 9, 0, tzinfo=DUB)
    w = Window.from_now(now)
    assert w.contains(now) and not w.contains(w.end)
    assert not w.contains(now - timedelta(minutes=1))

def test_filter_drops_finished_and_out_of_window_keeps_live():
    from src.window import filter_fixtures
    now = datetime(2026, 10, 1, 9, 0, tzinfo=DUB)
    w = Window.from_now(now)
    fx = [
        {"id": "a", "kickoff": now + timedelta(hours=2), "status": "scheduled"},
        {"id": "b", "kickoff": now - timedelta(hours=1), "status": "finished"},
        {"id": "c", "kickoff": now - timedelta(minutes=30), "status": "live"},
        {"id": "d", "kickoff": now + timedelta(hours=30), "status": "scheduled"},
    ]
    out = filter_fixtures(fx, w)
    assert [f["id"] for f in out] == ["a", "c"]
