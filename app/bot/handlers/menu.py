from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.start import MAIN_MENU_TEXT
from app.bot.keyboards import CB_AI_ANALYSIS, main_menu_keyboard
from app.bot.repository import get_or_create_user
from app.db.session import async_session_factory

router = Router(name="menu")

# Scanner is handled in app/bot/handlers/scanner.py, alerts in
# app/bot/handlers/alerts.py. Text and screenshot analysis are wired up in
# app/bot/handlers/analyze.py and screenshot.py.
AI_ANALYSIS_PROMPT = (
    "✨ Напишите тикер (например BTC или ETH 4h) или пришлите скриншот графика — пришлю разбор."
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
