from pydantic import BaseModel


class ScenarioSplit(BaseModel):
    """Deterministic 3-way probability split (TZ section 4.3: "Сумма
    вероятностей сценариев всегда = 100%"). Computed purely from
    ProbabilityResult — the LLM never sees or produces these percentages."""

    primary_direction: str  # "long" | "short"
    primary_confidence: float
    opposite_confidence: float
    neutral_confidence: float


class WhyBullet(BaseModel):
    sign: str  # "+" | "-"
    text: str


class AnalysisNarrative(BaseModel):
    """The only thing the LLM is allowed to produce: prose bullets
    referencing numbers it was given. See app/ai/prompt.py for the
    constraints enforced on this in the system prompt."""

    why: list[WhyBullet]


class AnalysisContext(BaseModel):
    """The compressed, already-final JSON handed to the LLM (TZ sections
    48-49). Every field here was computed by app/ta, app/probability, or
    app/risk — none of it is something the LLM is free to invent."""

    symbol: str
    tf: str
    price: float
    structure_bias: str
    rsi: float | None
    volume_trend: str
    nearest_support: float | None
    nearest_resistance: float | None
    scenarios: ScenarioSplit | None
    entry_low: float | None
    entry_high: float | None
    invalidation: float | None
    targets: list[float] | None
    risk_reward: float | None
    factors: dict[str, float]


class AnalysisResult(BaseModel):
    """Final, renderable analysis: deterministic numbers + LLM narrative."""

    symbol: str
    tf: str
    structure_bias: str
    scenarios: ScenarioSplit | None
    entry_low: float | None
    entry_high: float | None
    invalidation: float | None
    targets: list[float] | None
    risk_reward: float | None
    why: list[WhyBullet]
    disclaimer: str


class VisionExtraction(BaseModel):
    """What the vision model is allowed to read off a chart screenshot: the
    symbol/exchange/timeframe labels only. It must never report prices or
    indicator values — those always come from the Market Data Engine (TZ
    section 2.1: "скрин используется только для визуального контекста").
    Raw guesses here are not yet canonical symbols/timeframes; callers
    resolve them via app.market.symbols / app.ai.timeframe."""

    symbol_guess: str | None
    timeframe_guess: str | None
    exchange_guess: str | None
    confidence: str  # "high" | "medium" | "low" - the model's own self-assessment
