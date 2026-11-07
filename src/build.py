"""fixtures.json -> out/index.html. Usage: python3 -m src.build fixtures.json out/index.html"""
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .dedupe import dedupe
from .render import render
from .schema import parse_fixture
from .validate import check, check_page
from .window import Window, filter_fixtures, filter_modelled


def _dt(s):
    return datetime.fromisoformat(s)


def _load(raw: dict) -> dict:
    f = dict(raw)
    f["kickoff"] = _dt(f["kickoff"])
    f["models"] = [{**m, "fetched_at": _dt(m["fetched_at"])} for m in f.get("models", [])]
    return parse_fixture(f)


def build(src: str, dest: str, now: datetime, models_only: bool = True) -> dict:
    data = json.loads(Path(src).read_text())
    fixtures = dedupe([_load(f) for f in data["fixtures"]])
    window = Window.from_now(now)
    fixtures = filter_fixtures(fixtures, window)
    hidden = 0
    if models_only:
        shown = filter_modelled(fixtures)
        hidden, fixtures = len(fixtures) - len(shown), shown
    report = check(fixtures, window)
    html = render(fixtures, now=now, skipped=data.get("skipped", []), errors=report["errors"], hidden=hidden)
    page_errors = check_page(html, {f["sport"] for f in fixtures})
    if page_errors:
        report = {"ok": False, "errors": report["errors"] + page_errors}
        html = render(fixtures, now=now, skipped=data.get("skipped", []), errors=report["errors"], hidden=hidden)
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    Path(dest).write_text(html)
    return {**report, "count": len(fixtures), "hidden": hidden}


if __name__ == "__main__":
    r = build(sys.argv[1], sys.argv[2], datetime.now(ZoneInfo("Europe/Dublin")))
    print(json.dumps(r))
    sys.exit(0 if r["ok"] else 1)
