"""Probability Engine (TZ section 2.4): combines factor scores into a single
weighted direction score, then calibrates that into a bounded confidence
percentage. Deterministic, no LLM involved — the AI Reasoning Layer only
narrates this output, it never invents the numbers (TZ section 7)."""

from __future__ import annotations

import math

from app.probability.factors import (
    score_funding_oi,
    score_market_structure,
    score_momentum,
    score_support_resistance,
    score_volume,
)
from app.probability.schemas import ProbabilityResult
from app.probability.weights import DEFAULT_WEIGHTS, MAX_CONFIDENCE, MIN_CONFIDENCE
from app.ta.schemas import TechnicalSnapshot

# Weighted scores inside this band around zero are reported as "neutral"
# rather than a weak long/short call.
_NEUTRAL_DEAD_ZONE = 0.05

# Steepness of the score->confidence sigmoid; chosen so a fully one-sided
# score (magnitude 1.0) calibrates to just under MAX_CONFIDENCE.
_SIGMOID_STEEPNESS = 6.0


def calculate(snapshot: TechnicalSnapshot, funding_rate: float | None = None) -> ProbabilityResult:
    scores = {
        "market_structure": score_market_structure(snapshot),
        "momentum": score_momentum(snapshot),
        "volume": score_volume(snapshot),
        "support_resistance": score_support_resistance(snapshot),
    }
    funding_score = score_funding_oi(funding_rate)
    if funding_score is not None:
        scores["funding_oi"] = funding_score

    # Renormalize weights over whatever factors are actually available
    # (funding_oi is dropped for symbols without a futures market).
    active_weights = {name: DEFAULT_WEIGHTS[name] for name in scores}
    total_weight = sum(active_weights.values())
    normalized_weights = {name: w / total_weight for name, w in active_weights.items()}

    contributions = {name: scores[name] * normalized_weights[name] for name in scores}
    weighted_sum = sum(contributions.values())

    return ProbabilityResult(
        direction=_direction_from_score(weighted_sum),
        confidence=_calibrate_confidence(weighted_sum),
        factors={name: round(value, 4) for name, value in contributions.items()},
    )


def _direction_from_score(weighted_sum: float) -> str:
    if weighted_sum > _NEUTRAL_DEAD_ZONE:
        return "long"
    if weighted_sum < -_NEUTRAL_DEAD_ZONE:
        return "short"
    return "neutral"


def _calibrate_confidence(weighted_sum: float) -> float:
    magnitude = abs(weighted_sum)
    sigmoid = 1 / (1 + math.exp(-_SIGMOID_STEEPNESS * magnitude))
    confidence = MIN_CONFIDENCE + (MAX_CONFIDENCE - MIN_CONFIDENCE) * (sigmoid - 0.5) * 2
    return round(max(MIN_CONFIDENCE, min(MAX_CONFIDENCE, confidence)), 1)
