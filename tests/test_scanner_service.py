from app.market.schemas import Ticker
from app.scanner.service import (
    cache_scan_results,
    get_cached_scan_results,
    run_scan,
    scan_symbol,
)
from tests.factories import generate_range, generate_trend, make_candles


class FakeBinanceClient:
    def __init__(self, pool: dict[str, list[float]]) -> None:
        self.pool = pool

    async def get_klines(self, symbol, interval, limit=200):
        base = symbol.removesuffix("USDT")
        closes = self.pool.get(base, generate_range(cycles=5))
        return make_candles(closes)

    async def get_ticker_24hr(self, symbol):
        base = symbol.removesuffix("USDT")
        closes = self.pool.get(base, generate_range(cycles=5))
        return Ticker(symbol=symbol, price=closes[-1], price_change_percent_24h=1.0)


async def test_scan_symbol_returns_entry_for_directional_setup(fake_redis) -> None:
    from app.market.service import MarketDataEngine

    client = FakeBinanceClient({"BTC": generate_trend("up", cycles=6)})
    engine = MarketDataEngine(client, fake_redis)

    entry = await scan_symbol(engine, "BTC", "1h")

    assert entry is not None
    assert entry.symbol == "BTCUSDT@binance"
    assert entry.direction == "long"
    assert entry.risk_reward is not None
    assert entry.risk_level is not None


async def test_scan_symbol_unresolvable_returns_none(fake_redis) -> None:
    from app.market.service import MarketDataEngine

    client = FakeBinanceClient({})
    engine = MarketDataEngine(client, fake_redis)

    entry = await scan_symbol(engine, "not a real asset", "1h")
    assert entry is None


async def test_run_scan_covers_whole_pool(fake_redis, monkeypatch) -> None:
    from app.market.service import MarketDataEngine

    monkeypatch.setattr("app.scanner.service.SCANNER_SYMBOL_POOL", ("BTC", "ETH"))
    client = FakeBinanceClient(
        {"BTC": generate_trend("up", cycles=6), "ETH": generate_trend("down", cycles=6)}
    )
    engine = MarketDataEngine(client, fake_redis)

    entries = await run_scan(engine)

    symbols = {e.symbol for e in entries}
    assert symbols == {"BTCUSDT@binance", "ETHUSDT@binance"}


async def test_cache_round_trip(fake_redis) -> None:
    from app.scanner.schemas import ScannerEntry

    entries = [
        ScannerEntry(
            symbol="BTCUSDT@binance",
            tf="1h",
            direction="long",
            confidence=64.0,
            risk_reward=1.5,
            risk_level="medium",
            price=111800.0,
        )
    ]

    await cache_scan_results(fake_redis, entries)
    cached, updated_at = await get_cached_scan_results(fake_redis)

    assert len(cached) == 1
    assert cached[0].symbol == "BTCUSDT@binance"
    assert updated_at is not None


async def test_get_cached_scan_results_empty_when_no_cache(fake_redis) -> None:
    entries, updated_at = await get_cached_scan_results(fake_redis)
    assert entries == []
    assert updated_at is None
