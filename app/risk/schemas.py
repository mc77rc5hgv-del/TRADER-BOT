from pydantic import BaseModel


class RiskLevels(BaseModel):
    """Entry zone, stop, and targets for one directional setup — the numbers
    that land verbatim in Prediction.entry_low/entry_high/targets/invalidation
    (TZ sections 2.2 step 6, 4.3)."""

    direction: str  # "long" | "short"
    entry_low: float
    entry_high: float
    invalidation: float
    targets: list[float]
    risk_reward: float  # reward:risk ratio to the first target
