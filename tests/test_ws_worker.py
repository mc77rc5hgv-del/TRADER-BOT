import json

from app.market.ws_worker import LIVE_TICKER_HASH_KEY, build_stream_url, handle_message


def test_build_stream_url() -> None:
    url = build_stream_url(["btcusdt", "ethusdt"])
    assert url == ("wss://stream.binance.com:9443/stream?streams=btcusdt@ticker/ethusdt@ticker")


async def test_handle_message_updates_hash(fake_redis) -> None:
    raw = json.dumps(
        {
            "stream": "btcusdt@ticker",
            "data": {"s": "BTCUSDT", "c": "111480.50", "P": "2.14"},
        }
    )

    await handle_message(fake_redis, raw)

    stored = await fake_redis.hget(LIVE_TICKER_HASH_KEY, "BTCUSDT@binance")
    assert stored is not None
    payload = json.loads(stored)
    assert payload == {"price": 111480.50, "change_pct_24h": 2.14}


async def test_handle_message_ignores_malformed_payload(fake_redis) -> None:
    raw = json.dumps({"stream": "btcusdt@ticker", "data": {}})
    await handle_message(fake_redis, raw)
    assert await fake_redis.hget(LIVE_TICKER_HASH_KEY, "BTCUSDT@binance") is None
