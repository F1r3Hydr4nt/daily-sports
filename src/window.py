from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

DUBLIN = ZoneInfo("Europe/Dublin")


def to_dublin(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("naive datetime")
    return dt.astimezone(DUBLIN)


@dataclass(frozen=True)
class Window:
    start: datetime
    end: datetime

    @classmethod
    def from_now(cls, now: datetime) -> "Window":
        if now.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        now = to_dublin(now)
        # Add 24 elapsed hours in UTC so DST changes don't skew the window.
        end = (now.astimezone(ZoneInfo("UTC")) + timedelta(hours=24)).astimezone(DUBLIN)
        return cls(now, end)

    def contains(self, dt: datetime) -> bool:
        return self.start <= dt < self.end


def filter_fixtures(fixtures, window: Window):
    """Drop finished and out-of-window fixtures; keep started-but-live ones."""
    out = []
    for f in fixtures:
        if f["status"] == "finished":
            continue
        if f["status"] == "live" or window.contains(f["kickoff"]):
            out.append(f)
    return out
