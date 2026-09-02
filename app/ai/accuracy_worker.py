"""Prediction outcome evaluation background job (TZ section 6.6: "раз в
сутки"). Run as a separate process: `python -m app.ai.accuracy_worker`.
"""

from __future__ import annotations

import asyncio
import logging

from app.ai.accuracy import cache_accuracy_report, compute_accuracy_report, run_evaluation
from app.core.redis import get_redis
from app.db.session import async_session_factory
from app.market.router import get_market_data_engine

logger = logging.getLogger(__name__)

EVALUATION_INTERVAL_SECONDS = 24 * 60 * 60


async def run() -> None:
    market_engine = get_market_data_engine()
    redis = get_redis()

    while True:
        try:
            async with async_session_factory() as session:
                updated = await run_evaluation(session, market_engine)
                report = await compute_accuracy_report(session)
            await cache_accuracy_report(redis, report)
            logger.info(
                "Accuracy evaluation: updated %d predictions, cached report (%d resolved)",
                updated,
                report.resolved_predictions,
            )
        except Exception:
            logger.exception("Accuracy evaluation cycle failed")
        await asyncio.sleep(EVALUATION_INTERVAL_SECONDS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
