import pytest

from app.ta.service import analyze
from tests.factories import generate_trend, make_candles


def test_analyze_raises_on_empty_candles() -> None:
    with pytest.raises(ValueError, match="empty"):
        analyze([])


def test_analyze_returns_full_snapshot_for_long_history() -> None:
    # 42 cycles * 6 candles/cycle > 250, enough for EMA200 to resolve too.
    candles = make_candles(generate_trend("up", cycles=42))
    snapshot = analyze(candles)

    assert snapshot.price == candles[-1].close
    assert snapshot.rsi is not None
    assert snapshot.ema20 is not None
    assert snapshot.ema50 is not None
    assert snapshot.ema200 is not None
    assert snapshot.atr is not None
    assert snapshot.structure_bias == "bullish"


def test_analyze_returns_partial_snapshot_for_short_history() -> None:
    candles = make_candles(generate_trend("up", cycles=4))  # ~24 candles
    snapshot = analyze(candles)

    assert snapshot.ema20 is not None
    assert snapshot.ema200 is None  # not enough history yet, and that's fine
