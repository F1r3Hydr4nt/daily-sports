import re
from datetime import timedelta

ALIASES = {
    "man utd": "manchester united", "man united": "manchester united",
    "man city": "manchester city", "spurs": "tottenham hotspur", "tottenham": "tottenham hotspur",
    "wolves": "wolverhampton wanderers", "newcastle": "newcastle united",
    "west ham": "west ham united", "brighton": "brighton and hove albion",
}
TOLERANCE = timedelta(minutes=30)


def canon(name: str) -> str:
    n = re.sub(r"[^a-z0-9 ]", "", name.lower().replace("&", "and")).strip()
    n = re.sub(r"\b(fc|afc|cf)\b", "", n)
    n = re.sub(r"\s+", " ", n).strip()
    return ALIASES.get(n, n)


def _same(a, b) -> bool:
    return (a["sport"] == b["sport"] and canon(a["home"]) == canon(b["home"])
            and canon(a["away"]) == canon(b["away"])
            and abs(a["kickoff"] - b["kickoff"]) <= TOLERANCE)


def dedupe(fixtures):
    out = []
    for f in fixtures:
        for g in out:
            if _same(f, g):
                seen = {m["name"] for m in g["models"]}
                g["models"] += [m for m in f.get("models", []) if m["name"] not in seen]
                g["sources"] = sorted(set(g["sources"]) | set(f.get("sources", [])))
                break
        else:
            out.append({**f, "models": list(f.get("models", [])), "sources": list(f.get("sources", []))})
    return out
