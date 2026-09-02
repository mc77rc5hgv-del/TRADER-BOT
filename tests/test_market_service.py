import asyncio
from datetime import UTC, datetime

import pytest

from app.market.schemas import Candle, Ticker
from app.market.service import MarketDataEngine, UnsupportedExchangeError


class FakeBinanceClient:
    def __init__(self) -> None:
        self.klines_calls = 0
        self.ticker_calls = 0

    async def get_klines(self, symbol: str, interval: str, limit: int = 200) -> list[Candle]:
        self.klines_calls += 1
        now = datetime.now(UTC)
        return [
            Candle(
                open_time=now,
                open=100,
                high=105,
                low=95,
                close=102,
                volume=10,
                close_time=now,
            )
        ]

    async def get_ticker_24hr(self, symbol: str) -> Ticker:
        self.ticker_calls += 1
        return Ticker(symbol=symbol, price=102.0, price_change_percent_24h=1.5)


async def test_unknown_symbol_returns_none(fake_redis) -> None:
    engine = MarketDataEngine(FakeBinanceClient(), fake_redis)
    state = await engine.get_market_state("not a real asset", "1h")
    assert state is None


async def test_unsupported_timeframe_raises(fake_redis) -> None:
    engine = MarketDataEngine(FakeBinanceClient(), fake_redis)
    with pytest.raises(ValueError, match="Unsupported timeframe"):
        await engine.get_market_state("BTC", "3h")


async def test_fetches_and_caches_market_state(fake_redis) -> None:
    client = FakeBinanceClient()
    engine = MarketDataEngine(client, fake_redis, cache_ttl_seconds=60)

    state = await engine.get_market_state("BTC", "1h")

    assert state is not None
    assert state.symbol == "BTCUSDT@binance"
    assert state.tf == "1h"
    assert state.ticker.price == 102.0
    assert client.klines_calls == 1
    assert client.ticker_calls == 1


async def test_second_call_hits_cache_not_exchange(fake_redis) -> None:
    client = FakeBinanceClient()
    engine = MarketDataEngine(client, fake_redis, cache_ttl_seconds=60)

    await engine.get_market_state("BTC", "1h")
    await engine.get_market_state("btc/usdt", "1h")  # different alias, same canonical symbol

    assert client.klines_calls == 1
    assert client.ticker_calls == 1


async def test_parallel_identical_cache_misses_share_one_exchange_fetch(fake_redis) -> None:
    client = FakeBinanceClient()
    engine = MarketDataEngine(client, fake_redis, cache_ttl_seconds=60)

    states = await asyncio.gather(*(engine.get_market_state("BTC", "1h") for _ in range(100)))

    assert all(state is not None for state in states)
    assert client.klines_calls == 1
    assert client.ticker_calls == 1


async def test_non_binance_exchange_raises(fake_redis, monkeypatch) -> None:
    # normalize_symbol only ever resolves to @binance today (MVP scope); this
    # exercises the defensive guard that will matter once more exchanges are
    # onboarded (TZ section 27 mentions Binance/Bybit/OKX).
    monkeypatch.setattr("app.market.service.normalize_symbol", lambda raw: "BTCUSDT@bybit")
    engine = MarketDataEngine(FakeBinanceClient(), fake_redis)
    with pytest.raises(UnsupportedExchangeError):
        await engine.get_market_state("BTCUSDT@bybit", "1h")
