import json
from datetime import datetime
from zoneinfo import ZoneInfo
from src.build import build

def test_e2e_from_recorded_fixtures(tmp_path):
    out = tmp_path / "index.html"
    now = datetime(2026, 10, 1, 9, 0, tzinfo=ZoneInfo("Europe/Dublin"))
    result = build("fixtures/sample.json", str(out), now)
    html = out.read_text()
    assert result["ok"] and result["count"] == 2
    assert "Man Utd" in html and "Tennis" in html and "stale page" in html
    assert ">X<" not in html and "19:30" in html
