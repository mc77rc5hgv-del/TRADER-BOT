from pydantic import BaseModel


class TechnicalSnapshot(BaseModel):
    """Deterministic technical read on a symbol at the moment of analysis.
    This — not raw candles — is what the Probability and Risk engines, and
    eventually the compressed AI prompt, consume (TZ section 48-49)."""

    price: float
    rsi: float | None
    ema20: float | None
    ema50: float | None
    ema200: float | None
    atr: float | None
    volume_trend: str
    structure_bias: str
    nearest_support: float | None
    nearest_resistance: float | None
