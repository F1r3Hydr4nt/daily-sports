K = 20
DRAW_BASE = 0.27  # football draw share at equal strength (tunable baseline)


def expected(ra: float, rb: float, home_adv: float = 0) -> float:
    return 1 / (1 + 10 ** ((rb - ra - home_adv) / 400))


def update(ra: float, rb: float, score_a: float, home_adv: float = 0, k: float = K):
    delta = k * (score_a - expected(ra, rb, home_adv))
    return ra + delta, rb - delta


def three_way(ra: float, rb: float, home_adv: float = 0) -> dict:
    e = expected(ra, rb, home_adv)
    draw = DRAW_BASE * (1 - abs(2 * e - 1))
    home = e - draw / 2
    away = 1 - e - draw / 2
    return {"home": home * 100, "draw": draw * 100, "away": away * 100}
