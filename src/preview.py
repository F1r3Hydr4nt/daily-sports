"""Flashscore preview vs Predicd: does Flashscore's chosen market back Predicd's most likely result?"""


def predicd_top(fixture):
    """'home' | 'draw' | 'away' for Predicd's most likely outcome, or None when there is no Predicd model or a tie."""
    for m in fixture.get("models") or []:
        p = m.get("probs")
        if m.get("name") == "Predicd" and p and "draw" in p:
            best = max(p.values())
            tops = [k for k, v in p.items() if v == best]
            return tops[0] if len(tops) == 1 else None
    return None


def star(fixture) -> bool:
    """True when Flashscore's pick names outcomes (a result, double chance or win-by handicap) that include Predicd's top outcome."""
    pick = (fixture.get("preview") or {}).get("pick") or {}
    covers, top = pick.get("covers"), predicd_top(fixture)
    return bool(covers and top and top in covers)
