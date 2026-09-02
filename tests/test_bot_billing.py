from app.billing.service import PRO_PRICE_STARS, activate_pro_subscription
from app.bot.handlers.billing import INVOICE_PAYLOAD, _billing_text, on_pre_checkout_query
from app.users.models import User


class FakePreCheckoutQuery:
    def __init__(self, invoice_payload: str) -> None:
        self.invoice_payload = invoice_payload
        self.answered_ok: bool | None = None
        self.error_message: str | None = None

    async def answer(self, ok: bool, error_message: str | None = None) -> None:
        self.answered_ok = ok
        self.error_message = error_message


async def _make_user(db_session, telegram_id: int) -> User:
    user = User(telegram_id=telegram_id)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def test_billing_text_free_user_shows_price_and_buy_button(db_session) -> None:
    user = await _make_user(db_session, 1)

    text, show_buy_button = await _billing_text(db_session, user.id)

    assert "FREE" in text
    assert str(PRO_PRICE_STARS) in text
    assert show_buy_button is True


async def test_billing_text_pro_user_hides_buy_button(db_session) -> None:
    user = await _make_user(db_session, 2)
    await activate_pro_subscription(db_session, user.id, "telegram_stars", "charge_1")

    text, show_buy_button = await _billing_text(db_session, user.id)

    assert "PRO" in text
    assert show_buy_button is False


async def test_pre_checkout_accepts_known_payload() -> None:
    query = FakePreCheckoutQuery(INVOICE_PAYLOAD)

    await on_pre_checkout_query(query)

    assert query.answered_ok is True


async def test_pre_checkout_rejects_unknown_payload() -> None:
    query = FakePreCheckoutQuery("something_else")

    await on_pre_checkout_query(query)

    assert query.answered_ok is False
    assert query.error_message
