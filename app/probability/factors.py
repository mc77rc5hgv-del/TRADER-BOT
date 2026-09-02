"""Per-factor scoring: each function maps its input to a score in [-1, 1],
negative meaning bearish and positive meaning bullish. Kept separate from
weighting/calibration (app/probability/service.py) so each factor can be
tested and reasoned about independently."""

from __future__ import annotations

from app.ta.schemas import TechnicalSnapshot

# Funding rates rarely exceed this in either direction; used to normalize
# score_funding_oi() to roughly [-1, 1] without hardcoding a magic number inline.
_EXTREME_FUNDING_RATE = 0.05


def score_market_structure(snapshot: TechnicalSnapshot) -> float:
    if snapshot.structure_bias == "bullish":
        return 1.0
    if snapshot.structure_bias == "bearish":
        return -1.0
    return 0.0


def score_momentum(snapshot: TechnicalSnapshot) -> float:
    """RSI distance from the neutral 50 midpoint, clamped to [-1, 1]."""
    if snapshot.rsi is None:
        return 0.0
    return max(-1.0, min(1.0, (snapshot.rsi - 50) / 30))


def score_volume(snapshot: TechnicalSnapshot) -> float:
    """Rising volume reinforces the prevailing structure bias; it has no
    directional meaning on its own (falling/flat volume scores 0)."""
    if snapshot.volume_trend != "rising":
        return 0.0
    if snapshot.structure_bias == "bullish":
        return 1.0
    if snapshot.structure_bias == "bearish":
        return -1.0
    return 0.0


def score_support_resistance(snapshot: TechnicalSnapshot) -> float:
    """Price near support scores bullish (bounce likely); near resistance
    scores bearish. 0 when either level is unknown."""
    if snapshot.nearest_support is None or snapshot.nearest_resistance is None:
        return 0.0

    price_range = snapshot.nearest_resistance - snapshot.nearest_support
    if price_range <= 0:
        return 0.0

    position = (snapshot.price - snapshot.nearest_support) / price_range  # 0=support, 1=resistance
    return max(-1.0, min(1.0, 1 - 2 * position))


def score_funding_oi(funding_rate: float | None) -> float | None:
    """Contrarian read on extreme funding: very positive funding (crowded
    longs) leans bearish, very negative funding leans bullish. None when no
    futures market is available for this symbol (TZ section 2.4 note)."""
    if funding_rate is None:
        return None
    return max(-1.0, min(1.0, -funding_rate / _EXTREME_FUNDING_RATE))
