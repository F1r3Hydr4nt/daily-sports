"""Attach the day's written synopses (strengths + prediction, written by Claude from the Flashscore previews)
to the fixtures that have a preview.  Usage: python3 -m collect.synopses fixtures.json previews/YYYY-MM-DD.json
The synopsis file maps Flashscore match id -> {"strengths": {"home": str, "away": str}, "synopsis": str}."""
import json
import sys

MAX = 700


def _clean(s):
    return " ".join(s.split())[:MAX] if isinstance(s, str) and s.strip() else None


def apply_synopses(fixtures: list, synopses: dict) -> int:
    n = 0
    for f in fixtures:
        pv = f.get("preview")
        s = synopses.get(pv.get("match_id")) if pv else None
        if not isinstance(s, dict):
            continue
        syn = _clean(s.get("synopsis"))
        st = s.get("strengths") if isinstance(s.get("strengths"), dict) else {}
        strengths = {k: c for k in ("home", "away") if (c := _clean(st.get(k)))}
        if not syn and not strengths:
            continue
        if syn:
            pv["synopsis"] = syn
        if strengths:
            pv["strengths"] = strengths
        n += 1
    return n


if __name__ == "__main__":
    path, syn_path = sys.argv[1], sys.argv[2]
    data = json.load(open(path))
    done = apply_synopses(data["fixtures"], json.load(open(syn_path)))
    json.dump(data, open(path, "w"), indent=1)
    have = sum(1 for f in data["fixtures"] if f.get("preview"))
    print(f"synopses attached to {done} of {have} previews")
