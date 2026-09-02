from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.main import app
from app.market.router import get_market_data_engine
from app.market.schemas import Candle, MarketState, Ticker


class StubEngine:
    def __init__(self, state: MarketState | None = None, error: Exception | None = None) -> None:
        self._state = state
        self._error = error

    async def get_market_state(self, symbol: str, tf: str) -> MarketState | None:
        if self._error is not None:
            raise self._error
        return self._state


def _sample_state() -> MarketState:
    now = datetime.now(UTC)
    return MarketState(
        symbol="BTCUSDT@binance",
        tf="1h",
        ticker=Ticker(symbol="BTCUSDT", price=111480.5, price_change_percent_24h=2.14),
        candles=[Candle(open_time=now, open=100, high=105, low=95, close=102, volume=10, close_time=now)],
        fetched_at=now,
    )


def test_get_market_state_success() -> None:
    app.dependency_overrides[get_market_data_engine] = lambda: StubEngine(state=_sample_state())
    try:
        client = TestClient(app)
        response = client.get("/market/BTC/state", params={"tf": "1h"})
        assert response.status_code == 200
        body = response.json()
        assert body["symbol"] == "BTCUSDT@binance"
        assert body["ticker"]["price"] == 111480.5
    finally:
        app.dependency_overrides.clear()


def test_get_market_state_unknown_symbol_returns_404() -> None:
    app.dependency_overrides[get_market_data_engine] = lambda: StubEngine(state=None)
    try:
        client = TestClient(app)
        response = client.get("/market/notarealasset/state")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_get_market_state_bad_timeframe_returns_400() -> None:
    app.dependency_overrides[get_market_data_engine] = lambda: StubEngine(
        error=ValueError("Unsupported timeframe: 3h")
    )
    try:
        client = TestClient(app)
        response = client.get("/market/BTC/state", params={"tf": "3h"})
        assert response.status_code == 400
    finally:
        app.dependency_overrides.clear()
