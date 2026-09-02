"""Subscription screen and Telegram Stars payment flow (TZ section 8/9).
Stars payments don't need a payment provider token — send_invoice's
provider_token stays empty for currency="XTR" per Telegram's Bot API docs."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)

from app.billing.models import SubscriptionTier
from app.billing.service import (
    PRO_PRICE_STARS,
    PRO_SUBSCRIPTION_DURATION_DAYS,
    activate_pro_subscription,
    get_active_subscription,
    get_active_tier,
)
from app.bot.keyboards import CB_BILLING, CB_BILLING_BUY, billing_keyboard
from app.bot.repository import get_or_create_user
from app.db.session import async_session_factory

router = Router(name="billing")

INVOICE_PAYLOAD = "pro_subscription"
INVOICE_TITLE = "TRADE AI — PRO"
INVOICE_DESCRIPTION = (
    f"PRO-подписка на {PRO_SUBSCRIPTION_DURATION_DAYS} дней: больше AI-анализов в день "
    "и больше активных алертов."
)


def _tier_label(tier: SubscriptionTier) -> str:
    return "PRO" if tier == SubscriptionTier.PRO else "FREE"


async def _billing_text(session, user_id: int) -> tuple[str, bool]:
    """Returns (message text, whether to show the buy button)."""
    tier = await get_active_tier(session, user_id)
    if tier == SubscriptionTier.PRO:
        subscription = await get_active_subscription(session, user_id)
        expires_line = ""
        if subscription is not None and subscription.expires_at is not None:
            expires_line = f"\nДействует до: {subscription.expires_at:%Y-%m-%d}"
        return f"💳 Ваш тариф: PRO{expires_line}", False

    text = (
        "💳 Ваш тариф: FREE\n\n"
        "PRO даёт:\n"
        "• больше AI-анализов в день\n"
        "• больше активных алертов\n\n"
        f"Цена: {PRO_PRICE_STARS} ⭐ / {PRO_SUBSCRIPTION_DURATION_DAYS} дней"
    )
    return text, True


@router.callback_query(F.data == CB_BILLING)
async def on_billing(callback: CallbackQuery) -> None:
    async with async_session_factory() as session:
        user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
        text, show_buy_button = await _billing_text(session, user.id)

    await callback.message.answer(text, reply_markup=billing_keyboard(show_buy_button=show_buy_button))
    await callback.answer()


@router.callback_query(F.data == CB_BILLING_BUY)
async def on_billing_buy(callback: CallbackQuery) -> None:
    await callback.bot.send_invoice(
        chat_id=callback.from_user.id,
        title=INVOICE_TITLE,
        description=INVOICE_DESCRIPTION,
        payload=INVOICE_PAYLOAD,
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=INVOICE_TITLE, amount=PRO_PRICE_STARS)],
    )
    await callback.answer()


@router.pre_checkout_query()
async def on_pre_checkout_query(pre_checkout_query: PreCheckoutQuery) -> None:
    # Nothing to validate beyond the payload - a single fixed-price product.
    if pre_checkout_query.invoice_payload != INVOICE_PAYLOAD:
        await pre_checkout_query.answer(ok=False, error_message="Неизвестный товар.")
        return
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def on_successful_payment(message: Message) -> None:
    payment = message.successful_payment

    async with async_session_factory() as session:
        user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
        await activate_pro_subscription(
            session,
            user.id,
            payment_provider="telegram_stars",
            external_payment_id=payment.telegram_payment_charge_id,
        )

    await message.answer(
        f"✅ PRO активирован на {PRO_SUBSCRIPTION_DURATION_DAYS} дней. Спасибо за поддержку!"
    )
