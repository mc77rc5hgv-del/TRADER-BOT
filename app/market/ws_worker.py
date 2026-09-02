"""Shared Binance WS ingestion (TZ sections 5.1, 54): one connection covering
a fixed set of liquid symbols, fanned out to all users via Redis, instead of
opening a per-user connection to the exchange.

Run as a separate process: `python -m app.market.ws_worker`.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import websockets
from redis.asyncio import Redis

from app.core.redis import get_redis

logger = logging.getLogger(__name__)

BINANCE_WS_BASE = "wss://stream.binance.com:9443/stream"
LIVE_TICKER_HASH_KEY = "ticker:live"

# Top liquid symbols tracked live on the Home screen (TZ section 3.1).
# Widening this list is a config change, not a re-architecture.
TRACKED_SYMBOLS = ["btcusdt", "ethusdt", "solusdt", "xrpusdt", "bnbusdt"]

Connector = Callable[[str], Awaitable[Any]]


def build_stream_url(symbols: list[str]) -> str:
    streams = "/".join(f"{s}@ticker" for s in symbols)
    return f"{BINANCE_WS_BASE}?streams={streams}"


async def handle_message(redis: Redis, raw_message: str) -> None:
    payload = json.loads(raw_message)
    data = payload.get("data", {})
    symbol = data.get("s")  # e.g. "BTCUSDT"
    price = data.get("c")  # last price
    if not symbol or price is None:
        return

    canonical = f"{symbol}@binance"
    await redis.hset(
        LIVE_TICKER_HASH_KEY,
        canonical,
        json.dumps({"price": float(price), "change_pct_24h": float(data.get("P") or 0)}),
    )


async def run(connector: Connector | None = None) -> None:
    """`connector` is injectable so tests can supply a fake stream instead of
    hitting the real exchange; defaults to `websockets.connect`."""
    redis = get_redis()
    connect = connector or websockets.connect
    url = build_stream_url(TRACKED_SYMBOLS)

    backoff = 1
    while True:
        try:
            async with connect(url) as ws:
                logger.info("Connected to Binance WS stream (%d symbols)", len(TRACKED_SYMBOLS))
                backoff = 1
                async for message in ws:
                    await handle_message(redis, message)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Binance WS connection lost, reconnecting in %ss", backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
