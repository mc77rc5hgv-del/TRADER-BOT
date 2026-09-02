"""Synthetic candle series for TA/Probability/Risk engine tests. Not a
fixture of real market data — these build deliberately shaped price paths
(zigzag up/down/sideways) so structure detection has something unambiguous
to classify."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.market.schemas import Candle


def make_candles(
    closes: list[float], volumes: list[float] | None = None, wick: float = 0.05
) -> list[Candle]:
    """`wick` is added/subtracted from each candle's own close — not
    max/min(open, close) — so a candle's high/low never coincides with its
    neighbor's (which would happen whenever one candle's open equals the
    previous candle's close, i.e. always, here). That collision would make
    two adjacent candles share the same high/low and defeat the fractal
    swing detector in app.ta.structure, which requires a strict, unique
    extreme. The tradeoff is that these candles aren't fully realistic OHLC
    (high can sit below open on a big down candle) — fine for a synthetic
    fixture that only exists to test swing-point logic."""
    volumes = volumes or [100.0] * len(closes)
    start = datetime(2024, 1, 1, tzinfo=UTC)

    candles = []
    prev_close = closes[0]
    for i, close in enumerate(closes):
        open_price = prev_close
        high = close + wick
        low = close - wick
        open_time = start + timedelta(hours=i)
        candles.append(
            Candle(
                open_time=open_time,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=volumes[i],
                close_time=open_time + timedelta(hours=1),
            )
        )
        prev_close = close
    return candles


def generate_trend(
    direction: str,
    cycles: int = 4,
    impulse_len: int = 4,
    pullback_len: int = 2,
    impulse_step: float = 3.0,
    pullback_step: float = 2.0,
    start: float = 100.0,
) -> list[float]:
    """Zigzag price path with a net drift: a run of `impulse_len` candles in
    the trend direction, then a shorter/shallower `pullback_len` countermove,
    repeated `cycles` times. Produces well-formed swing highs/lows for
    app.ta.structure's fractal detector (see module docstring)."""
    sign = 1.0 if direction == "up" else -1.0
    closes = [start]
    price = start
    for _ in range(cycles):
        for _ in range(impulse_len):
            price += sign * impulse_step
            closes.append(price)
        for _ in range(pullback_len):
            price -= sign * pullback_step
            closes.append(price)
    return closes


def generate_range(
    cycles: int = 4, leg_len: int = 3, step: float = 2.0, start: float = 100.0
) -> list[float]:
    """Symmetric up/down legs of equal size — no net drift, alternating
    swing highs/lows of roughly equal height (a sideways market)."""
    closes = [start]
    price = start
    for _ in range(cycles):
        for _ in range(leg_len):
            price += step
            closes.append(price)
        for _ in range(leg_len):
            price -= step
            closes.append(price)
    return closes
