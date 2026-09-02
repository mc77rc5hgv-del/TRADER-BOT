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
from app.ai.usage import record_ai_request
from app.market.service import MarketDataEngine
from app.probability.service import calculate as calculate_probability
from app.risk.service import compute as compute_risk
from app.ta.service import analyze as analyze_technicals


class SymbolNotRecognizedError(Exception):
    """Raised when the input can't be resolved to a canonical symbol —
    callers should prompt the user to disambiguate rather than guess."""


async def run_chat_analysis(
    symbol_raw: str,
    tf: str,
    market_engine: MarketDataEngine,
    llm_provider: LLMProvider,
    db_session: AsyncSession,
    user_id: int | None,
) -> AnalysisResult:
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

    await record_ai_request(db_session, user_id, "chat_analysis", usage, latency_ms)

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
                source=PredictionSource.CHAT,
                model_version=usage.model,
            )
        )
        await db_session.commit()

    return result
