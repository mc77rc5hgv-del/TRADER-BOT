"""Deterministic scenario split (TZ section 4.3). Not LLM output — a fixed
formula over the Probability Engine's result, so the three percentages
always sum to exactly 100 and are reproducible/auditable."""

from __future__ import annotations

from app.ai.schemas import ScenarioSplit
from app.probability.schemas import ProbabilityResult

# Of the confidence "left over" after the primary scenario, this fraction is
# attributed to the neutral/range scenario and the rest to the opposite
# direction. 0.25 reproduces the TZ 4.3 worked example exactly (64/27/9).
_NEUTRAL_SHARE_OF_REMAINDER = 0.25


def split_scenarios(result: ProbabilityResult) -> ScenarioSplit | None:
    """None when the primary read is itself "neutral" — there's no
    directional trade to split against (see app/risk/service.py docstring)."""
    if result.direction == "neutral":
        return None

    remainder = 100.0 - result.confidence
    neutral = round(remainder * _NEUTRAL_SHARE_OF_REMAINDER, 1)
    opposite = round(remainder - neutral, 1)

    return ScenarioSplit(
        primary_direction=result.direction,
        primary_confidence=result.confidence,
        opposite_confidence=opposite,
        neutral_confidence=neutral,
    )
