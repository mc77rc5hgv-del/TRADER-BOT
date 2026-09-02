import pytest

from app.risk.service import classify_risk_level, compute
from app.ta.schemas import TechnicalSnapshot


def _snapshot(**overrides) -> TechnicalSnapshot:
    defaults = {
        "price": 100.0,
        "rsi": 60.0,
        "ema20": 99.0,
        "ema50": 98.0,
        "ema200": None,
        "atr": 2.0,
        "volume_trend": "rising",
        "structure_bias": "bullish",
        "nearest_support": 95.0,
        "nearest_resistance": 110.0,
    }
    defaults.update(overrides)
    return TechnicalSnapshot(**defaults)


def test_rejects_neutral_direction() -> None:
    with pytest.raises(ValueError, match="long"):
        compute(_snapshot(), "neutral")


def test_rejects_missing_atr() -> None:
    with pytest.raises(ValueError, match="ATR"):
        compute(_snapshot(atr=None), "long")


def test_long_setup_shape() -> None:
    result = compute(_snapshot(), "long")

    assert result.direction == "long"
    assert result.entry_low < result.entry_high
    assert result.invalidation < result.entry_low  # stop sits below the entry zone
    assert len(result.targets) == 2
    assert result.targets[0] < result.targets[1]  # target2 is further out than target1
    assert all(t > result.entry_high for t in result.targets)  # targets sit above entry
    assert result.risk_reward > 0


def test_short_setup_shape() -> None:
    result = compute(_snapshot(structure_bias="bearish", nearest_support=90.0, nearest_resistance=105.0), "short")

    assert result.direction == "short"
    assert result.entry_low < result.entry_high
    assert result.invalidation > result.entry_high  # stop sits above the entry zone
    assert len(result.targets) == 2
    assert result.targets[0] > result.targets[1]  # target2 is further out (lower) than target1
    assert all(t < result.entry_low for t in result.targets)  # targets sit below entry
    assert result.risk_reward > 0


def test_long_uses_nearby_support_as_stop() -> None:
    tight_support = compute(_snapshot(nearest_support=99.0), "long")
    no_support = compute(_snapshot(nearest_support=None), "long")
    # a support level just under the entry zone should produce a tighter stop
    # than the ATR fallback
    assert tight_support.invalidation > no_support.invalidation


def test_long_ignores_support_below_atr_fallback() -> None:
    # a support level far below the ATR-fallback stop shouldn't be used —
    # the fallback (entry_low - 1.0*atr) stays tighter/closer.
    far_support = compute(_snapshot(nearest_support=50.0), "long")
    no_support = compute(_snapshot(nearest_support=None), "long")
    assert far_support.invalidation == no_support.invalidation


def test_compute_includes_risk_level() -> None:
    result = compute(_snapshot(), "long")
    assert result.risk_level in ("low", "medium", "high")


def test_classify_risk_level_buckets_by_atr_over_price() -> None:
    assert classify_risk_level(_snapshot(price=100.0, atr=0.5)) == "low"  # 0.5%
    assert classify_risk_level(_snapshot(price=100.0, atr=2.0)) == "medium"  # 2%
    assert classify_risk_level(_snapshot(price=100.0, atr=5.0)) == "high"  # 5%


def test_classify_risk_level_defaults_to_medium_without_atr() -> None:
    assert classify_risk_level(_snapshot(atr=None)) == "medium"
