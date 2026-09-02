from fastapi.testclient import TestClient

from app.ai.dependencies import get_llm_provider
from app.ai.provider import LLMProvider, LLMUsage
from app.ai.schemas import AnalysisNarrative, WhyBullet
from app.db.session import get_session
from app.main import app
from app.market.router import get_market_data_engine
from app.market.schemas import Ticker
from app.market.service import MarketDataEngine
from app.webapp.router import get_validated_init_data
from tests.factories import generate_trend, make_candles


class FakeBinanceClient:
    def __init__(self, closes: list[float]) -> None:
        self.closes = closes

    async def get_klines(self, symbol, interval, limit=200):
        return make_candles(self.closes)

    async def get_ticker_24hr(self, symbol):
        return Ticker(symbol=symbol, price=self.closes[-1], price_change_percent_24h=1.0)


class FakeLLMProvider(LLMProvider):
    async def generate_structured(self, system_prompt, user_prompt, response_model):
        narrative = AnalysisNarrative(why=[WhyBullet(sign="+", text="test")])
        return narrative, LLMUsage(model="fake-model", input_tokens=10, output_tokens=5)

    async def extract_chart_info(self, image_bytes, media_type):
        raise NotImplementedError("not exercised by these tests")


def test_auth_rejects_missing_header() -> None:
    client = TestClient(app)
    response = client.post("/webapp/auth")
    assert response.status_code == 401


async def test_auth_creates_and_returns_user(db_session) -> None:
    async def fake_init_data(authorization=None):
        return {"user": {"id": 777, "username": "webapp_tester"}}

    async def fake_session():
        yield db_session

    app.dependency_overrides[get_validated_init_data] = fake_init_data
    app.dependency_overrides[get_session] = fake_session
    try:
        client = TestClient(app)
        response = client.post("/webapp/auth", headers={"Authorization": "tma fake"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["user"]["telegram_id"] == 777
    assert body["user"]["username"] == "webapp_tester"


async def test_auth_missing_user_in_init_data_returns_400(db_session) -> None:
    async def fake_init_data(authorization=None):
        return {}

    async def fake_session():
        yield db_session

    app.dependency_overrides[get_validated_init_data] = fake_init_data
    app.dependency_overrides[get_session] = fake_session
    try:
        client = TestClient(app)
        response = client.post("/webapp/auth", headers={"Authorization": "tma fake"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400


async def test_analyze_returns_resolved_setup(fake_redis, db_session) -> None:
    async def fake_init_data(authorization=None):
        return {"user": {"id": 777, "username": "webapp_tester"}}

    async def fake_session():
        yield db_session

    engine = MarketDataEngine(FakeBinanceClient(generate_trend("up", cycles=6)), fake_redis)

    app.dependency_overrides[get_validated_init_data] = fake_init_data
    app.dependency_overrides[get_session] = fake_session
    app.dependency_overrides[get_market_data_engine] = lambda: engine
    app.dependency_overrides[get_llm_provider] = lambda: FakeLLMProvider()
    try:
        client = TestClient(app)
        response = client.post(
            "/webapp/analyze",
            json={"symbol": "BTC", "tf": "1h"},
            headers={"Authorization": "tma fake"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "BTCUSDT@binance"
    assert body["scenarios"]["primary_direction"] == "long"
    assert body["disclaimer"]


async def test_analyze_unresolved_symbol_returns_404(fake_redis, db_session) -> None:
    async def fake_init_data(authorization=None):
        return {"user": {"id": 777, "username": "webapp_tester"}}

    async def fake_session():
        yield db_session

    engine = MarketDataEngine(FakeBinanceClient([100.0] * 30), fake_redis)

    app.dependency_overrides[get_validated_init_data] = fake_init_data
    app.dependency_overrides[get_session] = fake_session
    app.dependency_overrides[get_market_data_engine] = lambda: engine
    app.dependency_overrides[get_llm_provider] = lambda: FakeLLMProvider()
    try:
        client = TestClient(app)
        response = client.post(
            "/webapp/analyze",
            json={"symbol": "not a real asset", "tf": "1h"},
            headers={"Authorization": "tma fake"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
