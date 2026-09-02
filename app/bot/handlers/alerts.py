"""Price alert creation and listing (TZ section 13 step 9). Delivery lives
in app/alerts/worker.py — this module only handles the conversation."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.alerts.repository import (
    count_active_alerts,
    create_price_alert,
    list_active_alerts_for_user,
)
from app.alerts.service import describe_condition
from app.billing.service import get_tier_limits
from app.bot.keyboards import (
    CB_ALERT_CANCEL,
    CB_ALERT_DIRECTION_PREFIX,
    CB_ALERT_NEW,
    CB_ALERTS,
    alert_cancel_keyboard,
    alert_direction_keyboard,
    alerts_list_keyboard,
)
from app.bot.repository import get_or_create_user
from app.bot.states import AlertCreation
from app.db.session import async_session_factory
from app.market.symbols import normalize_symbol
from app.users.models import User

router = Router(name="alerts")


async def _render_alerts_list(session: AsyncSession, user: User) -> str:
    alerts = await list_active_alerts_for_user(session, user.id)
    if not alerts:
        return "🔔 У вас пока нет активных алертов."
    lines = [f"• {a.symbol} — {describe_condition(a.condition)}" for a in alerts]
    return "🔔 Ваши активные алерты:\n" + "\n".join(lines)


@router.callback_query(F.data == CB_ALERTS)
async def on_alerts(callback: CallbackQuery) -> None:
    async with async_session_factory() as session:
        user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
        text = await _render_alerts_list(session, user)

    await callback.message.answer(text, reply_markup=alerts_list_keyboard())
    await callback.answer()


@router.callback_query(F.data == CB_ALERT_NEW)
async def on_alert_new(callback: CallbackQuery, state: FSMContext) -> None:
    async with async_session_factory() as session:
        user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
        active_count = await count_active_alerts(session, user.id)
        limits = await get_tier_limits(session, user.id)

    if active_count >= limits.max_active_alerts:
        await callback.message.answer(
            f"Доступно до {limits.max_active_alerts} активных алертов на вашем тарифе. "
            "Дождитесь срабатывания одного из существующих, чтобы создать новый, "
            "или оформите PRO (кнопка «💳 Подписка» в меню) для более высокого лимита."
        )
        await callback.answer()
        return

    await state.set_state(AlertCreation.symbol)
    await callback.message.answer(
        "Какой тикер отслеживать? Например: BTC", reply_markup=alert_cancel_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == CB_ALERT_CANCEL)
async def on_alert_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer("Создание алерта отменено.")
    await callback.answer()


@router.message(AlertCreation.symbol)
async def on_alert_symbol(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if normalize_symbol(raw) is None:
        await message.answer(
            "Не удалось распознать тикер. Попробуйте ещё раз, например: BTC",
            reply_markup=alert_cancel_keyboard(),
        )
        return

    await state.update_data(symbol=raw.upper())
    await state.set_state(AlertCreation.direction)
    await message.answer(
        "Выше или ниже какой цены сообщить?", reply_markup=alert_direction_keyboard()
    )


@router.callback_query(AlertCreation.direction, F.data.startswith(CB_ALERT_DIRECTION_PREFIX))
async def on_alert_direction(callback: CallbackQuery, state: FSMContext) -> None:
    operator = callback.data.removeprefix(CB_ALERT_DIRECTION_PREFIX)
    await state.update_data(operator=operator)
    await state.set_state(AlertCreation.price)
    await callback.message.edit_text("Введите цену:")
    await callback.answer()


@router.message(AlertCreation.price)
async def on_alert_price(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip().replace(",", ".")
    try:
        price = float(raw)
    except ValueError:
        await message.answer(
            "Введите число, например: 111800", reply_markup=alert_cancel_keyboard()
        )
        return
    if price <= 0:
        await message.answer("Цена должна быть больше нуля.", reply_markup=alert_cancel_keyboard())
        return

    data = await state.get_data()
    symbol = data["symbol"]
    operator = data["operator"]
    await state.clear()

    async with async_session_factory() as session:
        user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
        await create_price_alert(session, user.id, symbol, {"operator": operator, "price": price})

    direction_label = "выше" if operator == "above" else "ниже"
    await message.answer(f"🔔 Алерт создан: {symbol} {direction_label} {price:g}")
