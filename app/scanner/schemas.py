from pydantic import BaseModel


class ScannerEntry(BaseModel):
    """One row of a scan (TZ section 3.4): direction/confidence/R:R/risk for
    a symbol, computed by the deterministic TA -> Probability -> Risk
    pipeline only — no LLM call (TZ section 95: scanning dozens of symbols
    must not cost AI budget)."""

    symbol: str
    tf: str
    direction: str  # "long" | "short" | "neutral"
    confidence: float
    risk_reward: float | None
    risk_level: str | None
    price: float
