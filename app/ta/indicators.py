"""Pure, deterministic indicator functions (TZ section 48: "большая часть
вычислений вообще без AI"). No I/O, no LLM calls — these operate only on
candle data already fetched by the Market Data Engine."""

from __future__ import annotations

from app.market.schemas import Candle


def ema_latest(values: list[float], period: int) -> float | None:
    """Latest EMA value, seeded with a plain SMA of the first `period` values."""
    if len(values) < period:
        return None
    k = 2 / (period + 1)
    ema_value = sum(values[:period]) / period
    for price in values[period:]:
        ema_value = price * k + ema_value * (1 - k)
    return ema_value


def rsi_latest(closes: list[float], period: int = 14) -> float | None:
    """Latest RSI using Wilder's smoothing."""
    if len(closes) < period + 1:
        return None

    changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(c, 0.0) for c in changes]
    losses = [max(-c, 0.0) for c in changes]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def atr_latest(candles: list[Candle], period: int = 14) -> float | None:
    """Latest Average True Range using Wilder's smoothing."""
    if len(candles) < period + 1:
        return None

    true_ranges = []
    for i in range(1, len(candles)):
        high, low, prev_close = candles[i].high, candles[i].low, candles[i - 1].close
        true_ranges.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))

    avg_tr = sum(true_ranges[:period]) / period
    for i in range(period, len(true_ranges)):
        avg_tr = (avg_tr * (period - 1) + true_ranges[i]) / period
    return avg_tr


def volume_trend(candles: list[Candle], window: int = 10) -> str:
    """ "rising" / "falling" / "flat" based on recent vs. prior average volume."""
    if len(candles) < window * 2:
        return "flat"

    recent_avg = sum(c.volume for c in candles[-window:]) / window
    prior_avg = sum(c.volume for c in candles[-window * 2 : -window]) / window
    if prior_avg == 0:
        return "flat"

    change = (recent_avg - prior_avg) / prior_avg
    if change > 0.15:
        return "rising"
    if change < -0.15:
        return "falling"
    return "flat"
