"""Risk Engine (TZ section 2.2 step 6): turns a TechnicalSnapshot + a chosen
direction into concrete entry/stop/target levels. Deterministic ATR-based
sizing, with the nearest support/resistance level used as the stop when it's
tighter than the ATR fallback. Only "long"/"short" setups are produced — a
"neutral" primary scenario has no trade to size (see TZ section 4.3: the
neutral scenario is reported as a price range, not a Prediction Ledger row)."""

from __future__ import annotations

from app.risk.schemas import RiskLevels
from app.ta.schemas import TechnicalSnapshot

ENTRY_BUFFER_ATR_MULT = 0.25
STOP_BUFFER_ATR_MULT = 0.10
STOP_FALLBACK_ATR_MULT = 1.0
TARGET_R_MULTIPLES = (1.5, 3.0)

# ATR/price ratio thresholds for the coarse risk_level label (TZ section 4.3's
# "Risk: Medium" line) — not a volatility forecast, just a bucket for display.
LOW_VOLATILITY_RATIO = 0.01
HIGH_VOLATILITY_RATIO = 0.03


def classify_risk_level(snapshot: TechnicalSnapshot) -> str:
    if snapshot.atr is None or snapshot.price <= 0:
        return "medium"
    volatility_ratio = snapshot.atr / snapshot.price
    if volatility_ratio < LOW_VOLATILITY_RATIO:
        return "low"
    if volatility_ratio < HIGH_VOLATILITY_RATIO:
        return "medium"
    return "high"


def compute(snapshot: TechnicalSnapshot, direction: str) -> RiskLevels:
    if direction not in ("long", "short"):
        raise ValueError('Risk engine only computes setups for "long" or "short"')
    if snapshot.atr is None:
        raise ValueError("Not enough candle history to compute ATR-based risk levels")

    price = snapshot.price
    atr = snapshot.atr

    if direction == "long":
        entry_low = price - ENTRY_BUFFER_ATR_MULT * atr
        entry_high = price

        fallback = entry_low - STOP_FALLBACK_ATR_MULT * atr
        if snapshot.nearest_support is not None and snapshot.nearest_support < entry_low:
            support_based = snapshot.nearest_support - STOP_BUFFER_ATR_MULT * atr
            # use whichever candidate sits closer to the entry — a support
            # level far below the ATR fallback would only widen the stop
            # for no structural benefit.
            invalidation = max(support_based, fallback)
        else:
            invalidation = fallback

        risk_distance = entry_low - invalidation
        targets = [entry_low + risk_distance * mult for mult in TARGET_R_MULTIPLES]
    else:
        entry_low = price
        entry_high = price + ENTRY_BUFFER_ATR_MULT * atr

        fallback = entry_high + STOP_FALLBACK_ATR_MULT * atr
        if snapshot.nearest_resistance is not None and snapshot.nearest_resistance > entry_high:
            resistance_based = snapshot.nearest_resistance + STOP_BUFFER_ATR_MULT * atr
            invalidation = min(resistance_based, fallback)
        else:
            invalidation = fallback

        risk_distance = invalidation - entry_high
        targets = [entry_high - risk_distance * mult for mult in TARGET_R_MULTIPLES]

    return RiskLevels(
        direction=direction,
        entry_low=round(entry_low, 8),
        entry_high=round(entry_high, 8),
        invalidation=round(invalidation, 8),
        targets=[round(t, 8) for t in targets],
        risk_reward=TARGET_R_MULTIPLES[0],
        risk_level=classify_risk_level(snapshot),
    )
