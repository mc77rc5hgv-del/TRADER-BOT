from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.start import MAIN_MENU_TEXT
from app.bot.keyboards import CB_AI_ANALYSIS, CB_SCANNER, main_menu_keyboard
from app.bot.repository import get_or_create_user
from app.db.session import async_session_factory

router = Router(name="menu")

# Scanner still reflects where it stands in the Phase 1 build sequence
# (TZ section 13) — its pipeline lands in a later step. Text and screenshot
# analysis are both wired up (see app/bot/handlers/analyze.py and screenshot.py).
# Alerts are handled in app/bot/handlers/alerts.py.
AI_ANALYSIS_PROMPT = (
    "✨ Напишите тикер (например BTC или ETH 4h) или пришлите скриншот графика — пришлю разбор."
)
SCANNER_PLACEHOLDER = (
    "🔥 Scanner ещё не запущен — появится вместе с фоновым обсчётом топ-активов "
    "(этап 10 плана разработки)."
)


@router.message(Command("app"))
async def cmd_app(message: Message) -> None:
    async with async_session_factory() as session:
        await get_or_create_user(session, message.from_user.id, message.from_user.username)
    await message.answer(MAIN_MENU_TEXT, reply_markup=main_menu_keyboard())


@router.callback_query(F.data == CB_AI_ANALYSIS)
async def on_ai_analysis(callback: CallbackQuery) -> None:
    await callback.message.answer(AI_ANALYSIS_PROMPT)
    await callback.answer()


@router.callback_query(F.data == CB_SCANNER)
async def on_scanner(callback: CallbackQuery) -> None:
    await callback.message.answer(SCANNER_PLACEHOLDER)
    await callback.answer()
