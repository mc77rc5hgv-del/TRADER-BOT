"""Scanner v0 background job (TZ section 13 step 10): recomputes the top
setups list on a fixed interval and caches it — never on a per-request
basis (TZ section 3.4).

Run as a separate process: `python -m app.scanner.worker`.
"""

from __future__ import annotations

import asyncio
import logging

from app.core.redis import get_redis
from app.market.router import get_market_data_engine
from app.scanner.service import cache_scan_results, run_scan

logger = logging.getLogger(__name__)

SCAN_INTERVAL_SECONDS = 10 * 60


async def run() -> None:
    market_engine = get_market_data_engine()
    redis = get_redis()

    while True:
        try:
            entries = await run_scan(market_engine)
            await cache_scan_results(redis, entries)
            logger.info("Scanner: cached %d entries", len(entries))
        except Exception:
            logger.exception("Scanner cycle failed")
        await asyncio.sleep(SCAN_INTERVAL_SECONDS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
