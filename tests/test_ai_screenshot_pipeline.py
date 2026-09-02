import io

from PIL import Image
from sqlalchemy import select

from app.ai.models import AIRequest, Prediction, PredictionSource, Screenshot
from app.ai.provider import LLMProvider, LLMUsage
from app.ai.schemas import AnalysisNarrative, VisionExtraction, WhyBullet
from app.ai.screenshot_pipeline import run_screenshot_analysis
from app.ai.screenshot_storage import ScreenshotStorage
from app.market.schemas import Ticker
from app.market.service import MarketDataEngine
from tests.factories import generate_trend, make_candles


class FakeBinanceClient:
    def __init__(self, closes: list[float]) -> None:
        self.closes = closes

    async def get_klines(self, symbol, interval, limit=200):
        return make_candles(self.closes)

    async def get_ticker_24hr(self, symbol):
        return Ticker(symbol=symbol, price=self.closes[-1], price_change_percent_24h=1.0)


class FakeLLMProvider(LLMProvider):
    def __init__(self, extraction: VisionExtraction) -> None:
        self.extraction = extraction

    async def generate_structured(self, system_prompt, user_prompt, response_model):
        narrative = AnalysisNarrative(why=[WhyBullet(sign="+", text="test")])
        return narrative, LLMUsage(model="fake-model", input_tokens=10, output_tokens=5)

    async def extract_chart_info(self, image_bytes, media_type):
        return self.extraction, LLMUsage(model="fake-model", input_tokens=200, output_tokens=20)


class FakeScreenshotStorage(ScreenshotStorage):
    def __init__(self) -> None:
        self.saved: dict[str, bytes] = {}

    async def save(self, key: str, data: bytes) -> None:
        self.saved[key] = data

    async def delete(self, key: str) -> None:
        self.saved.pop(key, None)


def _sample_image_bytes() -> bytes:
    image = Image.new("RGB", (20, 10), color=(0, 128, 255))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


async def test_resolved_symbol_runs_full_pipeline(fake_redis, db_session) -> None:
    closes = generate_trend("up", cycles=6)
    engine = MarketDataEngine(FakeBinanceClient(closes), fake_redis)
    provider = FakeLLMProvider(
        VisionExtraction(symbol_guess="BTC", timeframe_guess="1h", exchange_guess="Binance", confidence="high")
    )
    storage = FakeScreenshotStorage()

    outcome = await run_screenshot_analysis(
        _sample_image_bytes(), engine, provider, storage, db_session, user_id=42
    )

    assert outcome.status == "resolved"
    assert outcome.result is not None
    assert outcome.result.scenarios is not None

    screenshots = (await db_session.execute(select(Screenshot))).scalars().all()
    assert len(screenshots) == 1
    assert screenshots[0].user_id == 42
    assert screenshots[0].storage_key in storage.saved

    predictions = (await db_session.execute(select(Prediction))).scalars().all()
    assert len(predictions) == 1
    assert predictions[0].source == PredictionSource.SCREENSHOT

    ai_requests = (await db_session.execute(select(AIRequest))).scalars().all()
    types = {r.type for r in ai_requests}
    assert types == {"vision_extraction", "screenshot_analysis"}


async def test_ambiguous_symbol_returns_suggestions_without_prediction(fake_redis, db_session) -> None:
    closes = generate_trend("up", cycles=6)
    engine = MarketDataEngine(FakeBinanceClient(closes), fake_redis)
    provider = FakeLLMProvider(
        VisionExtraction(symbol_guess="BTX", timeframe_guess=None, exchange_guess=None, confidence="low")
    )
    storage = FakeScreenshotStorage()

    outcome = await run_screenshot_analysis(
        _sample_image_bytes(), engine, provider, storage, db_session, user_id=42
    )

    assert outcome.status == "ambiguous"
    assert "BTCUSDT@binance" in outcome.suggestions
    assert outcome.result is None

    assert (await db_session.execute(select(Prediction))).scalars().all() == []
    # the screenshot itself and the vision call are still recorded
    assert len((await db_session.execute(select(Screenshot))).scalars().all()) == 1
    assert len((await db_session.execute(select(AIRequest))).scalars().all()) == 1


async def test_unresolved_symbol_no_suggestions(fake_redis, db_session) -> None:
    closes = generate_trend("up", cycles=6)
    engine = MarketDataEngine(FakeBinanceClient(closes), fake_redis)
    provider = FakeLLMProvider(
        VisionExtraction(symbol_guess=None, timeframe_guess=None, exchange_guess=None, confidence="low")
    )
    storage = FakeScreenshotStorage()

    outcome = await run_screenshot_analysis(
        _sample_image_bytes(), engine, provider, storage, db_session, user_id=42
    )

    assert outcome.status == "unresolved"
    assert outcome.suggestions == []


async def test_invalid_image_short_circuits_before_storage(fake_redis, db_session) -> None:
    engine = MarketDataEngine(FakeBinanceClient([100.0] * 30), fake_redis)
    provider = FakeLLMProvider(
        VisionExtraction(symbol_guess="BTC", timeframe_guess="1h", exchange_guess=None, confidence="high")
    )
    storage = FakeScreenshotStorage()

    outcome = await run_screenshot_analysis(
        b"not an image", engine, provider, storage, db_session, user_id=42
    )

    assert outcome.status == "invalid_image"
    assert storage.saved == {}
    assert (await db_session.execute(select(Screenshot))).scalars().all() == []
