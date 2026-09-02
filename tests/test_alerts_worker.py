from datetime import UTC, datetime

from sqlalchemy import select

from app.alerts.models import Alert, AlertStatus
from app.alerts.repository import create_price_alert
from app.alerts.worker import check_alerts_once
from app.market.schemas import MarketState, Ticker
from app.users.models import User


class FakeBot:
    def __init__(self) -> None:
        self.sent: list[tuple[int, str]] = []

    async def send_message(self, chat_id: int, text: str) -> None:
        self.sent.append((chat_id, text))


class FakeMarketEngine:
    def __init__(self, price: float) -> None:
        self.price = price

    async def get_market_state(self, symbol: str, tf: str) -> MarketState:
        return MarketState(
            symbol=f"{symbol.upper()}USDT@binance",
            tf=tf,
            ticker=Ticker(symbol=f"{symbol.upper()}USDT", price=self.price, price_change_percent_24h=1.0),
            candles=[],
            fetched_at=datetime.now(UTC),
        )


async def _make_user(db_session, telegram_id: int) -> User:
    user = User(telegram_id=telegram_id)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def test_triggered_alert_is_marked_and_delivered(db_session) -> None:
    user = await _make_user(db_session, 999)
    alert = await create_price_alert(db_session, user.id, "BTC", {"operator": "above", "price": 100.0})

    bot = FakeBot()
    engine = FakeMarketEngine(price=105.0)

    await check_alerts_once(bot, engine, db_session)

    await db_session.refresh(alert)
    assert alert.status == AlertStatus.TRIGGERED
    assert alert.triggered_at is not None

    assert len(bot.sent) == 1
    chat_id, text = bot.sent[0]
    assert chat_id == 999
    assert "BTC" in text
    assert "105" in text


async def test_untriggered_alert_stays_active_and_silent(db_session) -> None:
    user = await _make_user(db_session, 1000)
    await create_price_alert(db_session, user.id, "BTC", {"operator": "above", "price": 200.0})

    bot = FakeBot()
    engine = FakeMarketEngine(price=105.0)

    await check_alerts_once(bot, engine, db_session)

    result = await db_session.execute(select(Alert).where(Alert.user_id == user.id))
    alert = result.scalar_one()
    assert alert.status == AlertStatus.ACTIVE
    assert bot.sent == []


async def test_triggered_alert_no_longer_reappears_next_cycle(db_session) -> None:
    user = await _make_user(db_session, 1001)
    await create_price_alert(db_session, user.id, "BTC", {"operator": "above", "price": 100.0})

    bot = FakeBot()
    engine = FakeMarketEngine(price=105.0)

    await check_alerts_once(bot, engine, db_session)
    await check_alerts_once(bot, engine, db_session)

    assert len(bot.sent) == 1  # not delivered twice


async def test_multiple_alerts_for_different_users(db_session) -> None:
    user1 = await _make_user(db_session, 2001)
    user2 = await _make_user(db_session, 2002)
    await create_price_alert(db_session, user1.id, "BTC", {"operator": "above", "price": 100.0})
    await create_price_alert(db_session, user2.id, "BTC", {"operator": "below", "price": 200.0})

    bot = FakeBot()
    engine = FakeMarketEngine(price=105.0)

    await check_alerts_once(bot, engine, db_session)

    chat_ids = {chat_id for chat_id, _ in bot.sent}
    assert chat_ids == {2001, 2002}
