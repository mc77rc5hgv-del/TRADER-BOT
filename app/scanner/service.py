"""Scanner v0 (TZ sections 3.4, 13 step 10): scans a fixed pool of liquid
symbols through the deterministic TA -> Probability -> Risk pipeline — no
LLM call, so scanning the whole pool costs nothing per request (TZ section
95: "экономия AI API"). Results are cached in Redis and recomputed by a
background job on a fixed interval (app/scanner/worker.py), never on-demand
per request (TZ section 3.4: "не on-demand на каждый клик")."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from pydantic import BaseModel
from redis.asyncio import Redis

from app.market.service import MarketDataEngine
from app.market.symbols import KNOWN_BASE_TICKERS
from app.probability.service import calculate as calculate_probability
from app.risk.service import compute as compute_risk
from app.scanner.schemas import ScannerEntry
from app.ta.service import analyze as analyze_technicals

logger = logging.getLogger(__name__)

# v0 pool = every base ticker the system can currently resolve (see
# app/market/symbols.py). TZ section 3.4 describes a top-30-50 pool; this
# grows automatically as the alias table grows.
SCANNER_SYMBOL_POOL: tuple[str, ...] = tuple(sorted(KNOWN_BASE_TICKERS))

# v0 scans a single timeframe for the whole pool — scanning multiple TFs
# would multiply the background job's Binance/compute load per cycle.
SCANNER_TF = "1h"

SCANNER_CACHE_KEY = "scanner:top_setups"
SCANNER_CACHE_TTL_SECONDS = 15 * 60  # upper bound of TZ's 5-15 min recompute window


class _ScanCache(BaseModel):
    entries: list[ScannerEntry]
    updated_at: str


async def scan_symbol(
    market_engine: MarketDataEngine, symbol: str, tf: str = SCANNER_TF
) -> ScannerEntry | None:
    market_state = await market_engine.get_market_state(symbol, tf)
    if market_state is None:
        return None

    snapshot = analyze_technicals(market_state.candles)
    probability = calculate_probability(snapshot)

    risk_reward = None
    risk_level = None
    if probability.direction in ("long", "short"):
        try:
            risk = compute_risk(snapshot, probability.direction)
            risk_reward = risk.risk_reward
            risk_level = risk.risk_level
        except ValueError:
            pass  # not enough candle history for ATR - report the read without sizing

    return ScannerEntry(
        symbol=market_state.symbol,
        tf=tf,
        direction=probability.direction,
        confidence=probability.confidence,
        risk_reward=risk_reward,
        risk_level=risk_level,
        price=snapshot.price,
    )


async def run_scan(market_engine: MarketDataEngine, tf: str = SCANNER_TF) -> list[ScannerEntry]:
    entries = []
    for symbol in SCANNER_SYMBOL_POOL:
        try:
            entry = await scan_symbol(market_engine, symbol, tf)
        except Exception:
            logger.exception("Scanner failed on symbol %s", symbol)
            continue
        if entry is not None:
            entries.append(entry)
    return entries


async def cache_scan_results(redis: Redis, entries: list[ScannerEntry]) -> None:
    payload = _ScanCache(entries=entries, updated_at=datetime.now(UTC).isoformat())
    await redis.set(SCANNER_CACHE_KEY, payload.model_dump_json(), ex=SCANNER_CACHE_TTL_SECONDS)


async def get_cached_scan_results(redis: Redis) -> tuple[list[ScannerEntry], str | None]:
    raw = await redis.get(SCANNER_CACHE_KEY)
    if raw is None:
        return [], None
    cache = _ScanCache.model_validate_json(raw)
    return cache.entries, cache.updated_at
