import pytest
from src.elo import expected, update, three_way

def test_equal_ratings_even():
    assert expected(1500, 1500) == pytest.approx(0.5)

def test_home_advantage_raises_home_win():
    assert expected(1500, 1500, home_adv=100) > 0.5

def test_update_zero_sum():
    a, b = update(1500, 1500, 1.0)
    assert a > 1500 and b < 1500 and a + b == pytest.approx(3000)

def test_draw_equal_ratings_no_move():
    assert update(1500, 1500, 0.5) == (1500, 1500)

def test_three_way_sums_100_and_ordering():
    p = three_way(1600, 1400, home_adv=60)
    assert sum(p.values()) == pytest.approx(100)
    assert p["home"] > p["away"] and p["draw"] > 0
