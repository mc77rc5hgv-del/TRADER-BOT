import httpx
import pytest

from app.market.binance_client import BinanceClient

KLINE_ROW = [
    1625097600000,
    "35000.00",
    "35500.00",
    "34800.00",
    "35200.00",
    "123.456",
    1625101199999,
    "4340000.00",
    1000,
    "60.0",
    "2100000.00",
    "0",
]


def _make_client(handler) -> BinanceClient:
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport, base_url="https://api.binance.com")
    return BinanceClient(client=http_client)


async def test_get_klines_parses_rows() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v3/klines"
        assert request.url.params["symbol"] == "BTCUSDT"
        assert request.url.params["interval"] == "1h"
        return httpx.Response(200, json=[KLINE_ROW])

    client = _make_client(handler)
    candles = await client.get_klines("BTCUSDT", "1h")

    assert len(candles) == 1
    candle = candles[0]
    assert candle.open == 35000.00
    assert candle.high == 35500.00
    assert candle.low == 34800.00
    assert candle.close == 35200.00
    assert candle.volume == 123.456


async def test_get_ticker_24hr_parses_fields() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v3/ticker/24hr"
        assert request.url.params["symbol"] == "BTCUSDT"
        return httpx.Response(200, json={"lastPrice": "111480.5", "priceChangePercent": "2.14"})

    client = _make_client(handler)
    ticker = await client.get_ticker_24hr("BTCUSDT")

    assert ticker.symbol == "BTCUSDT"
    assert ticker.price == 111480.5
    assert ticker.price_change_percent_24h == 2.14


async def test_get_klines_raises_on_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"code": -1121, "msg": "Invalid symbol."})

    client = _make_client(handler)
    with pytest.raises(httpx.HTTPStatusError):
        await client.get_klines("NOTASYMBOL", "1h")
