from app.ta.structure import classify_structure, find_swing_points, nearest_levels
from tests.factories import generate_range, generate_trend, make_candles


def test_uptrend_produces_higher_highs_and_higher_lows() -> None:
    candles = make_candles(generate_trend("up", cycles=5))
    highs, lows = find_swing_points(candles)

    assert len(highs) >= 2
    assert len(lows) >= 2
    assert highs[-1][1] > highs[-2][1]
    assert lows[-1][1] > lows[-2][1]


def test_uptrend_classifies_as_bullish() -> None:
    candles = make_candles(generate_trend("up", cycles=5))
    assert classify_structure(candles) == "bullish"


def test_downtrend_classifies_as_bearish() -> None:
    candles = make_candles(generate_trend("down", cycles=5))
    assert classify_structure(candles) == "bearish"


def test_range_classifies_as_neutral() -> None:
    candles = make_candles(generate_range(cycles=5))
    assert classify_structure(candles) == "neutral"


def test_not_enough_swings_is_neutral() -> None:
    candles = make_candles([100.0, 101.0, 100.5])
    assert classify_structure(candles) == "neutral"


def test_nearest_levels_bracket_current_price() -> None:
    candles = make_candles(generate_trend("up", cycles=5))
    current_price = candles[-1].close
    support, resistance = nearest_levels(candles, current_price)

    if support is not None:
        assert support < current_price
    if resistance is not None:
        assert resistance > current_price
