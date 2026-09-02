"""/analyze command and free-text symbol lookup (TZ section 4.2: "Свободный
текст и фото обрабатываются Intent Router (без обязательной команды)").
Screenshot input lives in app/bot/handlers/screenshot.py."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from app.ai.dependencies import get_llm_provider
from app.ai.pipeline import QuotaExceededError, SymbolNotRecognizedError, run_chat_analysis
from app.ai.render import render_text
from app.ai.timeframe import DEFAULT_TF
from app.bot.messages import quota_exceeded_text
from app.bot.repository import get_or_create_user
from app.db.session import async_session_factory
from app.market.router import get_market_data_engine
from app.market.schemas import ALLOWED_TIMEFRAMES

router = Router(name="analyze")

UNRECOGNIZED_SYMBOL_TEXT = (
    "Не удалось распознать актив. Попробуйте /analyze <тикер> [tf], например /analyze BTC 4h."
)


@router.message(Command("analyze"))
async def cmd_analyze(message: Message, command: CommandObject) -> None:
    args = (command.args or "").split()
    if not args:
        await message.answer("Использование: /analyze <тикер> [tf]\nНапример: /analyze BTC 4h")
        return

    symbol_raw = args[0]
    tf = args[1].lower() if len(args) > 1 else DEFAULT_TF
    if tf not in ALLOWED_TIMEFRAMES:
        await message.answer("Неизвестный таймфрейм. Доступные: " + ", ".join(ALLOWED_TIMEFRAMES))
        return

    await _run_and_reply(message, symbol_raw, tf, silent_on_miss=False)


@router.message(F.text & ~F.text.startswith("/"))
async def free_text_symbol(message: Message) -> None:
    text = (message.text or "").strip()
    if not text:
        return
    await _run_and_reply(message, text, DEFAULT_TF, silent_on_miss=True)


async def _run_and_reply(message: Message, symbol_raw: str, tf: str, silent_on_miss: bool) -> None:
    engine = get_market_data_engine()
    provider = get_llm_provider()

    async with async_session_factory() as session:
        user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
        try:
            result = await run_chat_analysis(symbol_raw, tf, engine, provider, session, user.id)
        except SymbolNotRecognizedError:
            if not silent_on_miss:
                await message.answer(UNRECOGNIZED_SYMBOL_TEXT)
            return
        except QuotaExceededError as exc:
            await message.answer(quota_exceeded_text(exc.limit))
            return

    await message.answer(render_text(result))
