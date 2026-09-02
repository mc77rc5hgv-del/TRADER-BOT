from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.models import AIRequest
from app.ai.pricing import estimate_cost_usd
from app.ai.provider import LLMUsage


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
