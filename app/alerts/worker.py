"""Alerts v0 delivery worker (TZ section 13 step 9): polls active price
alerts against live market state and notifies the owner in Telegram the
moment a condition is met. A simple polling loop is enough for MVP scale —
a proper task queue (TZ section 92) is later infrastructure, not needed yet.

Run as a separate process: `python -m app.alerts.worker`.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.timeframe import DEFAULT_TF
from app.alerts.models import AlertStatus
from app.alerts.repository import list_active_price_alerts_with_users
from app.alerts.service import describe_condition, evaluate_alert
from app.config import get_settings
from app.db.session import async_session_factory
from app.market.router import get_market_data_engine
from app.market.service import MarketDataEngine

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 30


async def check_alerts_once(bot: Bot, market_engine: MarketDataEngine, db_session: AsyncSession) -> None:
    rows = await list_active_price_alerts_with_users(db_session)

    for alert, user in rows:
        try:
            market_state = await market_engine.get_market_state(alert.symbol, DEFAULT_TF)
        except Exception:
            logger.exception("Failed to fetch market state for alert %s (%s)", alert.id, alert.symbol)
            continue
        if market_state is None:
            logger.warning("Alert %s has an unresolvable symbol %r — skipping", alert.id, alert.symbol)
            continue

        try:
            triggered = evaluate_alert(alert, market_state.ticker.price)
        except ValueError:
            logger.exception("Bad condition on alert %s", alert.id)
            continue

        if not triggered:
            continue

        # Mark triggered before attempting delivery so a failed send doesn't
        # leave the alert active to re-fire (and spam) next cycle.
        alert.status = AlertStatus.TRIGGERED
        alert.triggered_at = datetime.now(UTC)
        await db_session.commit()

        try:
            await bot.send_message(
                user.telegram_id,
                f"🔔 {alert.symbol}\n"
                f"Условие сработало: {describe_condition(alert.condition)}\n"
                f"Текущая цена: {market_state.ticker.price:g}",
            )
        except Exception:
            logger.exception("Failed to deliver alert %s to user %s", alert.id, user.telegram_id)


async def run(bot: Bot) -> None:
    market_engine = get_market_data_engine()
    while True:
        try:
            async with async_session_factory() as session:
                await check_alerts_once(bot, market_engine, session)
        except Exception:
            logger.exception("Alert check cycle failed")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
    bot = Bot(token=settings.telegram_bot_token)
    asyncio.run(run(bot))
