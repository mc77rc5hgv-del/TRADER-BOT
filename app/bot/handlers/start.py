from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import (
    CB_MARKETS_PREFIX,
    CB_RISK_PREFIX,
    CB_SKIP,
    CB_STYLE_PREFIX,
    main_reply_keyboard,
    preferred_markets_keyboard,
    risk_profile_keyboard,
    trading_style_keyboard,
)
from app.bot.repository import (
    get_or_create_user,
    set_preferred_markets,
    set_risk_profile,
    set_trading_style,
)
from app.bot.states import Onboarding
from app.db.session import async_session_factory
from app.users.models import PreferredMarket, RiskProfile, TradingStyle

router = Router(name="start")

WELCOME_TEXT = (
    "👋 Добро пожаловать в TRADE AI.\n\n"
    "Прежде чем начать — 3 коротких вопроса помогут подстроить бота под ваш стиль "
    "торговли. Каждый шаг можно пропустить."
)

MAIN_MENU_TEXT = "🤖 TRADE AI\n\nЧто хотите сделать?"


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    async with async_session_factory() as session:
        await get_or_create_user(session, message.from_user.id, message.from_user.username)

    await state.set_state(Onboarding.trading_style)
    await message.answer(WELCOME_TEXT)
    await message.answer("1/3. Какой у вас стиль торговли?", reply_markup=trading_style_keyboard())


@router.callback_query(Onboarding.trading_style, F.data.startswith(CB_STYLE_PREFIX))
async def onboarding_style(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.removeprefix(CB_STYLE_PREFIX)
    async with async_session_factory() as session:
        user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
        await set_trading_style(session, user, TradingStyle(value))
    await _advance_to_risk(callback, state)


@router.callback_query(Onboarding.trading_style, F.data == CB_SKIP)
async def onboarding_style_skip(callback: CallbackQuery, state: FSMContext) -> None:
    await _advance_to_risk(callback, state)


async def _advance_to_risk(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Onboarding.risk_profile)
    await callback.message.edit_text(
        "2/3. Какой у вас риск-профиль?", reply_markup=risk_profile_keyboard()
    )
    await callback.answer()


@router.callback_query(Onboarding.risk_profile, F.data.startswith(CB_RISK_PREFIX))
async def onboarding_risk(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.removeprefix(CB_RISK_PREFIX)
    async with async_session_factory() as session:
        user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
        await set_risk_profile(session, user, RiskProfile(value))
    await _advance_to_markets(callback, state)


@router.callback_query(Onboarding.risk_profile, F.data == CB_SKIP)
async def onboarding_risk_skip(callback: CallbackQuery, state: FSMContext) -> None:
    await _advance_to_markets(callback, state)


async def _advance_to_markets(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Onboarding.preferred_markets)
    await callback.message.edit_text(
        "3/3. Какие рынки вам интересны?", reply_markup=preferred_markets_keyboard()
    )
    await callback.answer()


@router.callback_query(Onboarding.preferred_markets, F.data.startswith(CB_MARKETS_PREFIX))
async def onboarding_markets(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.removeprefix(CB_MARKETS_PREFIX)
    async with async_session_factory() as session:
        user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
        await set_preferred_markets(session, user, PreferredMarket(value))
    await _finish_onboarding(callback, state)


@router.callback_query(Onboarding.preferred_markets, F.data == CB_SKIP)
async def onboarding_markets_skip(callback: CallbackQuery, state: FSMContext) -> None:
    await _finish_onboarding(callback, state)


async def _finish_onboarding(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Готово! Настройки сохранены ✅")
    # A persistent reply keyboard can only be attached to a new message, not
    # via edit_text - hence the follow-up message here.
    await callback.message.answer(MAIN_MENU_TEXT, reply_markup=main_reply_keyboard())
    await callback.answer()
