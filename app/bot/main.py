import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.handlers import accuracy, alerts, analyze, billing, menu, scanner, screenshot, start
from app.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    # MemoryStorage is fine for a single dev/staging instance; a multi-instance
    # deployment must switch to RedisStorage so FSM state is shared.
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start.router)
    dp.include_router(menu.router)
    dp.include_router(billing.router)
    dp.include_router(accuracy.router)
    dp.include_router(scanner.router)
    dp.include_router(screenshot.router)
    # alerts.router has state-scoped free-text handlers (symbol/price input
    # during alert creation) that must be checked before analyze.router's
    # catch-all, or the catch-all would swallow them.
    dp.include_router(alerts.router)
    # analyze.router registers a catch-all free-text handler last, so it
    # never shadows the commands/callbacks above it.
    dp.include_router(analyze.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
