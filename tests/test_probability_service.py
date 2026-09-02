from app.probability.service import calculate
from app.probability.weights import MAX_CONFIDENCE, MIN_CONFIDENCE
from app.ta.schemas import TechnicalSnapshot


def _snapshot(**overrides) -> TechnicalSnapshot:
    defaults = {
        "price": 100.0,
        "rsi": 50.0,
        "ema20": 100.0,
        "ema50": 100.0,
        "ema200": 100.0,
        "atr": 2.0,
        "volume_trend": "flat",
        "structure_bias": "neutral",
        "nearest_support": None,
        "nearest_resistance": None,
    }
    defaults.update(overrides)
    return TechnicalSnapshot(**defaults)


def test_fully_bullish_snapshot_is_long_with_high_confidence() -> None:
    snapshot = _snapshot(structure_bias="bullish", rsi=80.0, volume_trend="rising")
    result = calculate(snapshot)

    assert result.direction == "long"
    assert result.confidence > 70.0
    assert result.confidence <= MAX_CONFIDENCE


def test_fully_bearish_snapshot_is_short_with_high_confidence() -> None:
    snapshot = _snapshot(structure_bias="bearish", rsi=20.0, volume_trend="rising")
    result = calculate(snapshot)

    assert result.direction == "short"
    assert result.confidence > 70.0


def test_neutral_snapshot_is_neutral_with_minimum_confidence() -> None:
    snapshot = _snapshot()
    result = calculate(snapshot)

    assert result.direction == "neutral"
    assert result.confidence == MIN_CONFIDENCE


def test_confidence_always_within_bounds() -> None:
    for structure in ("bullish", "bearish", "neutral"):
        for rsi in (5.0, 50.0, 95.0):
            result = calculate(_snapshot(structure_bias=structure, rsi=rsi))
            assert MIN_CONFIDENCE <= result.confidence <= MAX_CONFIDENCE


def test_factors_sum_to_weighted_score_matching_direction() -> None:
    snapshot = _snapshot(structure_bias="bullish", rsi=70.0, volume_trend="rising")
    result = calculate(snapshot)
    assert sum(result.factors.values()) > 0
    assert set(result.factors) == {"market_structure", "momentum", "volume", "support_resistance"}


def test_funding_rate_included_when_provided() -> None:
    snapshot = _snapshot(structure_bias="bullish")
    result = calculate(snapshot, funding_rate=0.03)
    assert "funding_oi" in result.factors


def test_funding_rate_excluded_when_absent() -> None:
    snapshot = _snapshot(structure_bias="bullish")
    result = calculate(snapshot, funding_rate=None)
    assert "funding_oi" not in result.factors


def test_extreme_positive_funding_pulls_confidence_down_for_long() -> None:
    snapshot = _snapshot(structure_bias="bullish", rsi=60.0, volume_trend="rising")
    without_funding = calculate(snapshot, funding_rate=None)
    with_extreme_funding = calculate(snapshot, funding_rate=0.05)
    assert with_extreme_funding.confidence <= without_funding.confidence
