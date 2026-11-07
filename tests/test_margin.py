import math

from src.score import derive_score, predicted_score


def _probs(lh, la, n=12):
    pm = lambda lam, k: math.exp(-lam) * lam ** k / math.factorial(k)
    h = d = a = 0.0
    for i in range(n):
        for j in range(n):
            p = pm(lh, i) * pm(la, j)
            if i > j:
                h += p
            elif i == j:
                d += p
            else:
                a += p
    return {"home": h * 100, "draw": d * 100, "away": a * 100}


def test_derive_score_recovers_poisson_means():
    for lh, la in [(2.0, 0.6), (1.2, 1.1), (0.7, 1.9), (3.0, 0.4)]:
        gh, ga = derive_score(_probs(lh, la))
        assert abs(gh - lh) < 0.15 and abs(ga - la) < 0.15, (lh, la, gh, ga)


def test_derive_score_margin_sign_follows_favourite():
    gh, ga = derive_score({"home": 15, "draw": 22, "away": 63})
    assert ga > gh


def test_predicted_score_prefers_published_score():
    f = {"models": [{"score": {"home": 3.7, "away": 2.2}, "probs": None}]}
    assert predicted_score(f) == {"home": 3.7, "away": 2.2, "margin": 1.5, "derived": False}


def test_predicted_score_derives_from_win_probabilities():
    f = {"models": [{"probs": {"home": 66, "draw": 20, "away": 14}}]}
    s = predicted_score(f)
    assert s["derived"] is True and s["margin"] > 0 and s["home"] > s["away"]


def test_predicted_score_none_without_models():
    assert predicted_score({"models": []}) is None
    assert predicted_score({"models": [{"probs": {"home": 60, "away": 40}}]}) is None  # two-way: no goals model
