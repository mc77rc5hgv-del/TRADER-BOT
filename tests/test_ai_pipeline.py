import pytest
from sqlalchemy import select

from app.ai.models import AIRequest, Prediction
from app.ai.pipeline import QuotaExceededError, SymbolNotRecognizedError, run_chat_analysis
from app.ai.provider import LLMProvider, LLMUsage
from app.ai.schemas import AnalysisNarrative, WhyBullet
from app.billing.models import SubscriptionTier
from app.billing.service import TIER_LIMITS
from app.market.schemas import Ticker
from app.market.service import MarketDataEngine
from app.users.models import User
from tests.factories import generate_trend, make_candles


class FakeBinanceClient:
    def __init__(self, closes: list[float]) -> None:
        self.closes = closes
        self.klines_calls = 0

    async def get_klines(self, symbol, interval, limit=200):
        self.klines_calls += 1
        return make_candles(self.closes)

    async def get_ticker_24hr(self, symbol):
        return Ticker(symbol=symbol, price=self.closes[-1], price_change_percent_24h=1.0)


class FakeLLMProvider(LLMProvider):
    async def generate_structured(self, system_prompt, user_prompt, response_model):
        narrative = AnalysisNarrative(why=[WhyBullet(sign="+", text="test")])
        return narrative, LLMUsage(model="fake-model", input_tokens=10, output_tokens=5)

    async def extract_chart_info(self, image_bytes, media_type):
        raise NotImplementedError("not exercised by these tests")


async def test_unresolved_symbol_raises(fake_redis, db_session) -> None:
    engine = MarketDataEngine(FakeBinanceClient([100.0] * 30), fake_redis)

    with pytest.raises(SymbolNotRecognizedError):
        await run_chat_analysis(
            "not a real asset", "1h", engine, FakeLLMProvider(), db_session, user_id=None
        )


async def test_long_setup_persists_prediction_and_ai_request(fake_redis, db_session) -> None:
    closes = generate_trend("up", cycles=6)  # bullish structure, enough history for ATR/RSI
    engine = MarketDataEngine(FakeBinanceClient(closes), fake_redis)

    result = await run_chat_analysis(
        "BTC", "1h", engine, FakeLLMProvider(), db_session, user_id=None
    )

    assert result.scenarios is not None
    assert result.scenarios.primary_direction == "long"
    assert result.entry_low is not None

    predictions = (await db_session.execute(select(Prediction))).scalars().all()
    assert len(predictions) == 1
    prediction = predictions[0]
    assert prediction.symbol == "BTCUSDT@binance"
    assert prediction.tf == "1h"
    assert prediction.direction.value == "long"
    assert prediction.source.value == "chat"
    assert prediction.model_version == "fake-model"

    ai_requests = (await db_session.execute(select(AIRequest))).scalars().all()
    assert len(ai_requests) == 1
    assert ai_requests[0].type == "chat_analysis"


async def test_neutral_direction_records_usage_but_no_prediction(
    fake_redis, db_session, monkeypatch
) -> None:
    closes = generate_trend("up", cycles=6)
    engine = MarketDataEngine(FakeBinanceClient(closes), fake_redis)

    from app.probability.schemas import ProbabilityResult

    monkeypatch.setattr(
        "app.ai.pipeline.calculate_probability",
        lambda snapshot, funding_rate=None: ProbabilityResult(
            direction="neutral", confidence=35.0, factors={}
        ),
    )

    result = await run_chat_analysis(
        "BTC", "1h", engine, FakeLLMProvider(), db_session, user_id=None
    )

    assert result.scenarios is None
    assert (await db_session.execute(select(Prediction))).scalars().all() == []
    ai_requests = (await db_session.execute(select(AIRequest))).scalars().all()
    assert len(ai_requests) == 1


async def test_symbol_aliases_hit_shared_cache(fake_redis, db_session) -> None:
    closes = generate_trend("up", cycles=6)
    client = FakeBinanceClient(closes)
    engine = MarketDataEngine(client, fake_redis)

    await run_chat_analysis("BTC", "1h", engine, FakeLLMProvider(), db_session, user_id=None)
    await run_chat_analysis("btc/usdt", "1h", engine, FakeLLMProvider(), db_session, user_id=None)

    # second call reused the cached market state - no second upstream fetch
    assert client.klines_calls == 1
    predictions = (await db_session.execute(select(Prediction))).scalars().all()
    assert len(predictions) == 2  # two independent analyses/predictions...
    assert len({p.symbol for p in predictions}) == 1  # ...of the same canonical symbol


async def _make_user(db_session, telegram_id: int) -> User:
    user = User(telegram_id=telegram_id)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def test_analysis_under_quota_succeeds(fake_redis, db_session) -> None:
    user = await _make_user(db_session, 100)
    closes = generate_trend("up", cycles=6)
    engine = MarketDataEngine(FakeBinanceClient(closes), fake_redis)

    result = await run_chat_analysis("BTC", "1h", engine, FakeLLMProvider(), db_session, user.id)

    assert result.scenarios is not None


async def test_analysis_at_quota_raises(fake_redis, db_session) -> None:
    user = await _make_user(db_session, 101)
    closes = generate_trend("up", cycles=6)
    engine = MarketDataEngine(FakeBinanceClient(closes), fake_redis)

    free_limit = TIER_LIMITS[SubscriptionTier.FREE].ai_analyses_per_day
    for _ in range(free_limit):
        await run_chat_analysis("BTC", "1h", engine, FakeLLMProvider(), db_session, user.id)

    with pytest.raises(QuotaExceededError):
        await run_chat_analysis("BTC", "1h", engine, FakeLLMProvider(), db_session, user.id)
