"""Predicted score and margin for a fixture.

Published scores (Odds Shark) are used as they are. For football, Predicd publishes only win/draw/loss
percentages, so an expected scoreline is *derived* by fitting independent Poisson goal means to those
percentages. It is our estimate from the model's probabilities, not a score the source published."""
import math

_N = 11  # goals considered per side


def _pmf(lam):
    out, p = [], math.exp(-lam)
    for k in range(_N):
        out.append(p)
        p *= lam / (k + 1)
    return out


def _outcome(lh, la):
    ph, pa = _pmf(lh), _pmf(la)
    home = draw = away = 0.0
    for i, a in enumerate(ph):
        for j, b in enumerate(pa):
            if i > j:
                home += a * b
            elif i == j:
                draw += a * b
            else:
                away += a * b
    return home, draw, away


def derive_score(probs):
    """Expected goals (home, away) whose Poisson win/draw/loss split best matches probs (percent)."""
    total = probs["home"] + probs["draw"] + probs["away"]
    th, tdr, ta = (probs[k] / total for k in ("home", "draw", "away"))
    best = (9.0, 1.3, 1.1)
    lo_h, hi_h, lo_a, hi_a, step = 0.05, 5.0, 0.05, 5.0, 0.25
    for _ in range(5):
        best = (9.0, best[1], best[2])
        h = lo_h
        while h <= hi_h + 1e-9:
            a = lo_a
            while a <= hi_a + 1e-9:
                ph, pd, pa = _outcome(h, a)
                err = (ph - th) ** 2 + (pd - tdr) ** 2 + (pa - ta) ** 2
                if err < best[0]:
                    best = (err, h, a)
                a += step
            h += step
        _, bh, ba = best
        span = step * 2
        lo_h, hi_h, lo_a, hi_a = max(0.02, bh - span), bh + span, max(0.02, ba - span), ba + span
        step /= 4
    return round(best[1], 2), round(best[2], 2)


def predicted_score(fixture):
    """{'home','away','margin','derived'} or None. margin = home minus away (negative = away favoured)."""
    models = fixture.get("models") or []
    for m in models:
        sc = m.get("score")
        if sc:
            return {"home": sc["home"], "away": sc["away"], "margin": round(sc["home"] - sc["away"], 2),
                    "derived": False}
    for m in models:
        p = m.get("probs")
        if p and "draw" in p:
            h, a = derive_score(p)
            return {"home": h, "away": a, "margin": round(h - a, 2), "derived": True}
    return None


def win_gap(fixture):
    """Percentage-point gap between the two sides' win probabilities for two-way models (e.g. tennis), else None.
    With several two-way models the gaps are averaged. Football keeps its goal margin, so models with a draw
    outcome are ignored here."""
    gaps = []
    for m in fixture.get("models") or []:
        p = m.get("probs")
        if p and "draw" not in p and "home" in p and "away" in p and p["home"] + p["away"] > 0:
            gaps.append(abs(p["home"] - p["away"]) / (p["home"] + p["away"]) * 100)
    return round(sum(gaps) / len(gaps), 2) if gaps else None


def _lean(m):
    """'home' | 'away' | None for one model: the side it favours, None for a draw/tie/level."""
    p, sc = m.get("probs"), m.get("score")
    if p and "home" in p and "away" in p:
        best = max(p.values())
        tops = [k for k, v in p.items() if v == best]
        return tops[0] if len(tops) == 1 and tops[0] in ("home", "away") else None
    if sc:
        d = sc["home"] - sc["away"]
        return "home" if d > 0 else "away" if d < 0 else None
    return None


def favourite(fixture):
    """The side the model(s) favour, 'home' or 'away', else None (no models, a draw/tie, or the models disagree).
    The page bolds only this side, so bold always means 'the prediction', never merely 'first listed'."""
    leans = [_lean(m) for m in fixture.get("models") or []]
    return leans[0] if leans and leans[0] and all(x == leans[0] for x in leans) else None
