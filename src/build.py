"""fixtures.json -> out/index.html. Usage: python3 -m src.build fixtures.json out/index.html"""
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .dedupe import dedupe
from .render import render
from .schema import parse_fixture
from .validate import check
from .window import Window, filter_fixtures


def _dt(s):
    return datetime.fromisoformat(s)


def _load(raw: dict) -> dict:
    f = dict(raw)
    f["kickoff"] = _dt(f["kickoff"])
    f["models"] = [{**m, "fetched_at": _dt(m["fetched_at"])} for m in f.get("models", [])]
    return parse_fixture(f)


def build(src: str, dest: str, now: datetime) -> dict:
    data = json.loads(Path(src).read_text())
    fixtures = dedupe([_load(f) for f in data["fixtures"]])
    window = Window.from_now(now)
    fixtures = filter_fixtures(fixtures, window)
    report = check(fixtures, window)
    html = render(fixtures, now=now, skipped=data.get("skipped", []), errors=report["errors"])
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    Path(dest).write_text(html)
    return {**report, "count": len(fixtures)}


if __name__ == "__main__":
    r = build(sys.argv[1], sys.argv[2], datetime.now(ZoneInfo("Europe/Dublin")))
    print(json.dumps(r))
    sys.exit(0 if r["ok"] else 1)
