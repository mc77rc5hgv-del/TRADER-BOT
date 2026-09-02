from datetime import UTC, datetime, timedelta

from app.market.schemas import Candle
from app.ta.indicators import atr_latest, ema_latest, rsi_latest, volume_trend


def _flat_range_candles(count: int, high: float = 105, low: float = 95, close: float = 100) -> list[Candle]:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    return [
        Candle(
            open_time=start + timedelta(hours=i),
            open=close,
            high=high,
            low=low,
            close=close,
            close_time=start + timedelta(hours=i, minutes=59),
            volume=100.0,
        )
        for i in range(count)
    ]


def test_ema_latest_none_when_insufficient_data() -> None:
    assert ema_latest([1.0, 2.0, 3.0], period=20) is None


def test_ema_latest_of_constant_series_equals_that_constant() -> None:
    values = [50.0] * 30
    assert ema_latest(values, period=20) == 50.0


def test_rsi_latest_none_when_insufficient_data() -> None:
    assert rsi_latest([1.0, 2.0, 3.0], period=14) is None


def test_rsi_latest_all_gains_is_100() -> None:
    closes = [100.0 + i for i in range(20)]  # strictly increasing
    assert rsi_latest(closes, period=14) == 100.0


def test_rsi_latest_all_losses_is_0() -> None:
    closes = [100.0 - i for i in range(20)]  # strictly decreasing
    assert rsi_latest(closes, period=14) == 0.0


def test_atr_latest_none_when_insufficient_data() -> None:
    assert atr_latest(_flat_range_candles(5), period=14) is None


def test_atr_latest_constant_true_range() -> None:
    candles = _flat_range_candles(20, high=105, low=95, close=100)
    assert atr_latest(candles, period=14) == 10.0


def test_volume_trend_flat_when_insufficient_data() -> None:
    candles = _flat_range_candles(10)
    assert volume_trend(candles, window=10) == "flat"


def test_volume_trend_rising() -> None:
    prior = _flat_range_candles(10)
    for c in prior:
        c.volume = 100.0
    recent = _flat_range_candles(10)
    for c in recent:
        c.volume = 200.0
    assert volume_trend(prior + recent, window=10) == "rising"


def test_volume_trend_falling() -> None:
    prior = _flat_range_candles(10)
    for c in prior:
        c.volume = 200.0
    recent = _flat_range_candles(10)
    for c in recent:
        c.volume = 100.0
    assert volume_trend(prior + recent, window=10) == "falling"
