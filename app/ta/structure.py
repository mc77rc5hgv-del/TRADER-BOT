"""Market structure (HH/HL/LH/LL) and nearest support/resistance, per TZ
section 12 (Smart Money / Price Action module — simplified for MVP scope,
see TZ section 1's "не входит в MVP")."""

from __future__ import annotations

from app.market.schemas import Candle


def find_swing_points(
    candles: list[Candle], left: int = 2, right: int = 2
) -> tuple[list[tuple[int, float]], list[tuple[int, float]]]:
    """Simple fractal swing detection: a candle is a swing high/low when its
    high/low is the strict extreme within `left` candles before and `right`
    candles after it. Returns (swing_highs, swing_lows) as (index, price)."""
    highs: list[tuple[int, float]] = []
    lows: list[tuple[int, float]] = []
    n = len(candles)

    for i in range(left, n - right):
        window = candles[i - left : i + right + 1]
        window_highs = [c.high for c in window]
        window_lows = [c.low for c in window]

        if candles[i].high == max(window_highs) and window_highs.count(candles[i].high) == 1:
            highs.append((i, candles[i].high))
        if candles[i].low == min(window_lows) and window_lows.count(candles[i].low) == 1:
            lows.append((i, candles[i].low))

    return highs, lows


def classify_structure(candles: list[Candle]) -> str:
    """ "bullish" when the last two swing highs and lows are both rising
    (HH+HL), "bearish" when both are falling (LH+LL), "neutral" otherwise
    (mixed signals or not enough swing points yet)."""
    highs, lows = find_swing_points(candles)

    votes = []
    if len(highs) >= 2 and highs[-1][1] != highs[-2][1]:
        votes.append("bullish" if highs[-1][1] > highs[-2][1] else "bearish")
    if len(lows) >= 2 and lows[-1][1] != lows[-2][1]:
        votes.append("bullish" if lows[-1][1] > lows[-2][1] else "bearish")

    if not votes:
        return "neutral"
    if all(v == "bullish" for v in votes):
        return "bullish"
    if all(v == "bearish" for v in votes):
        return "bearish"
    return "neutral"


def nearest_levels(
    candles: list[Candle], current_price: float
) -> tuple[float | None, float | None]:
    """Nearest swing-low below price (support) and swing-high above price
    (resistance)."""
    highs, lows = find_swing_points(candles)

    supports = [price for _, price in lows if price < current_price]
    resistances = [price for _, price in highs if price > current_price]

    nearest_support = max(supports) if supports else None
    nearest_resistance = min(resistances) if resistances else None
    return nearest_support, nearest_resistance
