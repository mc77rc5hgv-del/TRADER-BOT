"""End-to-end text analysis pipeline (TZ section 13, step 5): Market Data ->
Technical Analysis -> Probability -> Risk -> AI Reasoning, with the result
of any long/short setup recorded in the Prediction Ledger. This is the one
place that wires the deterministic engines together with the LLM narrator —
callers (bot handlers, future API endpoints) should go through this rather
than calling the engines directly."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.models import Prediction, PredictionDirection, PredictionSource
from app.ai.models import RiskLevel as PredictionRiskLevel
from app.ai.provider import LLMProvider
from app.ai.reasoning import analyze as run_reasoning
from app.ai.schemas import AnalysisResult
from app.ai.usage import count_analysis_requests_today, record_ai_request
from app.billing.service import get_tier_limits
from app.market.service import MarketDataEngine
from app.probability.service import calculate as calculate_probability
from app.risk.service import compute as compute_risk
from app.ta.service import analyze as analyze_technicals


class SymbolNotRecognizedError(Exception):
    """Raised when the input can't be resolved to a canonical symbol —
    callers should prompt the user to disambiguate rather than guess."""


class QuotaExceededError(Exception):
    """Raised when the user has hit their tier's daily AI-analysis limit
    (TZ section 8). Callers should point the user at a PRO upgrade rather
    than retry."""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        super().__init__(f"Daily AI analysis quota exceeded ({limit}/day)")


# Must stay in sync with app.ai.usage.ANALYSIS_REQUEST_TYPES - these are the
# ai_requests.type values that count against the daily quota.
_AI_REQUEST_TYPE_BY_SOURCE = {
    PredictionSource.CHAT: "chat_analysis",
    PredictionSource.SCREENSHOT: "screenshot_analysis",
    PredictionSource.SCANNER: "scanner_analysis",
}


async def run_chat_analysis(
    symbol_raw: str,
    tf: str,
    market_engine: MarketDataEngine,
    llm_provider: LLMProvider,
    db_session: AsyncSession,
    user_id: int | None,
    source: PredictionSource = PredictionSource.CHAT,
) -> AnalysisResult:
    if user_id is not None:
        limits = await get_tier_limits(db_session, user_id)
        used_today = await count_analysis_requests_today(db_session, user_id)
        if used_today >= limits.ai_analyses_per_day:
            raise QuotaExceededError(limits.ai_analyses_per_day)

    market_state = await market_engine.get_market_state(symbol_raw, tf)
    if market_state is None:
        raise SymbolNotRecognizedError(symbol_raw)

    snapshot = analyze_technicals(market_state.candles)
    probability = calculate_probability(snapshot)

    risk = None
    if probability.direction in ("long", "short"):
        try:
            risk = compute_risk(snapshot, probability.direction)
        except ValueError:
            # Not enough candle history for ATR - report the read without a
            # sized trade rather than failing the whole analysis.
            risk = None

    started_at = datetime.now(UTC)
    result, usage = await run_reasoning(
        llm_provider, market_state.symbol, tf, snapshot, probability, risk
    )
    latency_ms = int((datetime.now(UTC) - started_at).total_seconds() * 1000)

    await record_ai_request(db_session, user_id, _AI_REQUEST_TYPE_BY_SOURCE[source], usage, latency_ms)

    if risk is not None:
        db_session.add(
            Prediction(
                user_id=user_id,
                symbol=market_state.symbol,
                tf=tf,
                direction=PredictionDirection(probability.direction),
                confidence=probability.confidence,
                entry_low=risk.entry_low,
                entry_high=risk.entry_high,
                targets=risk.targets,
                invalidation=risk.invalidation,
                risk_level=PredictionRiskLevel(risk.risk_level),
                factors=probability.factors,
                source=source,
                model_version=usage.model,
            )
        )
        await db_session.commit()

    return result
