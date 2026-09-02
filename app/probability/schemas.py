from pydantic import BaseModel


class ProbabilityResult(BaseModel):
    direction: str  # "long" | "short" | "neutral"
    confidence: float  # calibrated to [MIN_CONFIDENCE, MAX_CONFIDENCE] (weights.py)
    factors: dict[str, float]  # factor name -> weighted contribution, stored verbatim
    # in Prediction.factors (TZ section 6.2/6.6) so calibration can be audited later.
