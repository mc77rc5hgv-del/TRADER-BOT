from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.models import AIRequest
from app.ai.pricing import estimate_cost_usd
from app.ai.provider import LLMUsage

# ai_requests.type values that count against the daily "AI analyses" quota
# (TZ section 8: "5 AI-анализов в день (текст + скриншот суммарно)").
# vision_extraction is deliberately excluded — it's internal bookkeeping for
# the screenshot flow's vision call, not a second analysis on top of it.
ANALYSIS_REQUEST_TYPES = ("chat_analysis", "screenshot_analysis")


async def count_analysis_requests_today(session: AsyncSession, user_id: int) -> int:
    start_of_day = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    result = await session.execute(
        select(func.count())
        .select_from(AIRequest)
        .where(
            AIRequest.user_id == user_id,
            AIRequest.type.in_(ANALYSIS_REQUEST_TYPES),
            AIRequest.created_at >= start_of_day,
        )
    )
    return result.scalar_one()


async def record_ai_request(
    session: AsyncSession,
    user_id: int | None,
    request_type: str,
    usage: LLMUsage,
    latency_ms: int,
) -> AIRequest:
    """Persists one LLM call for the cost/DAU dashboard (TZ section 11)."""
    record = AIRequest(
        user_id=user_id,
        type=request_type,
        tokens_in=usage.input_tokens,
        tokens_out=usage.output_tokens,
        cost_usd=estimate_cost_usd(usage.model, usage.input_tokens, usage.output_tokens),
        latency_ms=latency_ms,
        model=usage.model,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record
