"""Chart screenshot analysis (TZ sections 2.1, 13 step 6). The image is only
used to identify the symbol/timeframe via a vision model — the actual
market numbers always come from the Market Data Engine, never the picture."""

from __future__ import annotations

import io

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.ai.dependencies import get_llm_provider, get_screenshot_storage
from app.ai.models import PredictionSource
from app.ai.pipeline import QuotaExceededError, run_chat_analysis
from app.ai.render import render_text
from app.ai.screenshot_pipeline import ScreenshotAnalysisOutcome, run_screenshot_analysis
from app.ai.timeframe import DEFAULT_TF
from app.bot.messages import quota_exceeded_text
from app.bot.repository import get_or_create_user
from app.config import get_settings
from app.db.session import async_session_factory
from app.market.router import get_market_data_engine

router = Router(name="screenshot")

CB_SCREENSHOT_SYMBOL_PREFIX = "ss_sym:"

TOO_LARGE_TEXT = "Файл слишком большой — пришлите скриншот меньшего размера."
INVALID_IMAGE_TEXT = "Не получилось открыть файл как изображение — пришлите скриншот ещё раз."
UNRESOLVED_TEXT = (
    "Не удалось распознать тикер на скриншоте. Попробуйте прислать текстом, "
    "например: /analyze BTC 4h."
)
AMBIGUOUS_TEXT = "Не уверен в тикере на скриншоте — это один из этих активов?"


@router.message(F.photo)
async def on_photo(message: Message) -> None:
    settings = get_settings()
    photo = message.photo[-1]

    if photo.file_size and photo.file_size > settings.screenshot_max_bytes:
        await message.answer(TOO_LARGE_TEXT)
        return

    file_info = await message.bot.get_file(photo.file_id)
    buffer = io.BytesIO()
    await message.bot.download_file(file_info.file_path, destination=buffer)
    image_bytes = buffer.getvalue()

    if len(image_bytes) > settings.screenshot_max_bytes:
        await message.answer(TOO_LARGE_TEXT)
        return

    await message.answer("⏳ Распознаю график...")

    engine = get_market_data_engine()
    provider = get_llm_provider()
    storage = get_screenshot_storage()

    async with async_session_factory() as session:
        user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
        try:
            outcome = await run_screenshot_analysis(image_bytes, engine, provider, storage, session, user.id)
        except QuotaExceededError as exc:
            await message.answer(quota_exceeded_text(exc.limit))
            return

    await _reply_to_outcome(message, outcome)


async def _reply_to_outcome(message: Message, outcome: ScreenshotAnalysisOutcome) -> None:
    if outcome.status == "resolved":
        await message.answer(render_text(outcome.result))
    elif outcome.status == "ambiguous":
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=symbol.split("@")[0].removesuffix("USDT"),
                        callback_data=f"{CB_SCREENSHOT_SYMBOL_PREFIX}{symbol}",
                    )
                ]
                for symbol in outcome.suggestions
            ]
        )
        await message.answer(AMBIGUOUS_TEXT, reply_markup=keyboard)
    elif outcome.status == "invalid_image":
        await message.answer(INVALID_IMAGE_TEXT)
    else:
        await message.answer(UNRESOLVED_TEXT)


@router.callback_query(F.data.startswith(CB_SCREENSHOT_SYMBOL_PREFIX))
async def on_symbol_choice(callback: CallbackQuery) -> None:
    symbol = callback.data.removeprefix(CB_SCREENSHOT_SYMBOL_PREFIX)

    engine = get_market_data_engine()
    provider = get_llm_provider()

    async with async_session_factory() as session:
        user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
        try:
            result = await run_chat_analysis(
                symbol, DEFAULT_TF, engine, provider, session, user.id, source=PredictionSource.SCREENSHOT
            )
        except QuotaExceededError as exc:
            await callback.message.answer(quota_exceeded_text(exc.limit))
            await callback.answer()
            return

    await callback.message.answer(render_text(result))
    await callback.answer()
