from sqlalchemy import select

from app.ai.models import AIRequest
from app.ai.pricing import estimate_cost_usd
from app.ai.provider import LLMUsage
from app.ai.usage import record_ai_request
from app.users.models import User


def test_estimate_cost_usd_known_model() -> None:
    cost = estimate_cost_usd("claude-opus-5", input_tokens=1_000_000, output_tokens=1_000_000)
    assert cost == 30.0  # $5 in + $25 out per 1M tokens


def test_estimate_cost_usd_unknown_model_is_zero() -> None:
    assert estimate_cost_usd("some-unknown-model", 1000, 1000) == 0.0


async def test_record_ai_request_persists_row(db_session) -> None:
    user = User(telegram_id=123456, username="tester")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    usage = LLMUsage(model="claude-opus-5", input_tokens=500, output_tokens=100)
    record = await record_ai_request(db_session, user.id, "analysis", usage, latency_ms=850)

    assert record.id is not None
    assert record.cost_usd > 0
    assert record.latency_ms == 850

    result = await db_session.execute(select(AIRequest).where(AIRequest.user_id == user.id))
    stored = result.scalar_one()
    assert stored.model == "claude-opus-5"
    assert stored.tokens_in == 500
    assert stored.tokens_out == 100
