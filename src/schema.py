from datetime import datetime

STATUSES = {"scheduled", "live", "finished"}
KINDS = {"official-feed", "statistical-model", "ai-model", "human-pick"}
MODEL_FIELDS = ("name", "kind", "source", "url", "fetched_at", "probs")


def _aware(dt):
    return isinstance(dt, datetime) and dt.tzinfo is not None


def parse_fixture(d: dict) -> dict:
    for k in ("sport", "home", "away", "kickoff", "status"):
        if k not in d:
            raise ValueError(f"missing {k}")
    if not _aware(d["kickoff"]):
        raise ValueError("kickoff must be timezone-aware")
    if d["status"] not in STATUSES:
        raise ValueError(f"bad status {d['status']}")
    for m in d.get("models", []):
        for k in MODEL_FIELDS:
            if k not in m:
                raise ValueError(f"model missing {k}")
        if m["kind"] not in KINDS:
            raise ValueError(f"bad model kind {m['kind']}")
        if not _aware(m["fetched_at"]):
            raise ValueError("fetched_at must be timezone-aware")
        if not m["probs"] or any(not 0 <= v <= 100 for v in m["probs"].values()):
            raise ValueError("probabilities must be within 0..100")
    return d
