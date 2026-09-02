from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from redis.asyncio import Redis

from app.market.binance_client import BinanceClient
from app.market.schemas import ALLOWED_TIMEFRAMES, MarketState
from app.market.symbols import normalize_symbol, split_canonical_symbol

CACHE_KEY_PREFIX = "market_state"


class UnsupportedExchangeError(Exception):
    """Raised when a canonical symbol resolves to an exchange the MVP
    doesn't integrate yet (only Binance ships in Phase 1, TZ section 5.1)."""


class MarketDataEngine:
    """Single shared ingestion/query layer: many users asking about the same
    symbol+timeframe reuse one cached fetch instead of each hitting Binance
    directly (TZ section 5.3 — this is the mechanism behind "100,000 users
    != 100,000 separate market analyses")."""

    def __init__(self, client: BinanceClient, redis: Redis, cache_ttl_seconds: int = 60) -> None:
        self._client = client
        self._redis = redis
        self._cache_ttl_seconds = cache_ttl_seconds
        self._inflight: dict[str, asyncio.Task[MarketState]] = {}
        self._inflight_guard = asyncio.Lock()

    async def get_market_state(self, symbol_raw: str, tf: str) -> MarketState | None:
        """Returns None when the symbol can't be resolved. Raises ValueError
        for an unsupported timeframe and UnsupportedExchangeError for a
        recognized symbol on an exchange the MVP doesn't integrate yet."""
        if tf not in ALLOWED_TIMEFRAMES:
            raise ValueError(f"Unsupported timeframe: {tf}")

        canonical = normalize_symbol(symbol_raw)
        if canonical is None:
            return None

        cache_key = f"{CACHE_KEY_PREFIX}:{canonical}:{tf}"
        cached = await self._redis.get(cache_key)
        if cached:
            return MarketState.model_validate_json(cached)

        # Single-flight: a burst of identical cache misses shares one exchange
        # fetch inside this worker instead of stampeding Binance.
        async with self._inflight_guard:
            task = self._inflight.get(cache_key)
            if task is None:
                task = asyncio.create_task(self._fetch_and_cache(canonical, tf, cache_key))
                self._inflight[cache_key] = task

        try:
            return await asyncio.shield(task)
        finally:
            if task.done():
                async with self._inflight_guard:
                    if self._inflight.get(cache_key) is task:
                        self._inflight.pop(cache_key, None)

    async def _fetch_and_cache(self, canonical: str, tf: str, cache_key: str) -> MarketState:
        # Re-check after joining the critical section: another process may
        # have populated Redis while this worker was waiting.
        cached = await self._redis.get(cache_key)
        if cached:
            return MarketState.model_validate_json(cached)

        pair, exchange = split_canonical_symbol(canonical)
        if exchange != "binance":
            raise UnsupportedExchangeError(exchange)

        candles = await self._client.get_klines(pair, tf)
        ticker = await self._client.get_ticker_24hr(pair)
        state = MarketState(
            symbol=canonical,
            tf=tf,
            ticker=ticker,
            candles=candles,
            fetched_at=datetime.now(UTC),
        )
        await self._redis.set(cache_key, state.model_dump_json(), ex=self._cache_ttl_seconds)
        return state
