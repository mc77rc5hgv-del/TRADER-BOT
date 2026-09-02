from app.alerts.repository import (
    count_active_alerts,
    create_price_alert,
    list_active_alerts_for_user,
    list_active_price_alerts_with_users,
)
from app.users.models import User


async def _make_user(db_session, telegram_id: int) -> User:
    user = User(telegram_id=telegram_id)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def test_create_and_list_price_alert(db_session) -> None:
    user = await _make_user(db_session, 1)

    alert = await create_price_alert(db_session, user.id, "BTC", {"operator": "above", "price": 100.0})

    assert alert.id is not None
    assert alert.symbol == "BTC"

    alerts = await list_active_alerts_for_user(db_session, user.id)
    assert len(alerts) == 1
    assert alerts[0].id == alert.id


async def test_count_active_alerts(db_session) -> None:
    user = await _make_user(db_session, 2)
    assert await count_active_alerts(db_session, user.id) == 0

    await create_price_alert(db_session, user.id, "BTC", {"operator": "above", "price": 100.0})
    await create_price_alert(db_session, user.id, "ETH", {"operator": "below", "price": 50.0})

    assert await count_active_alerts(db_session, user.id) == 2


async def test_count_active_alerts_is_per_user(db_session) -> None:
    user1 = await _make_user(db_session, 3)
    user2 = await _make_user(db_session, 4)
    await create_price_alert(db_session, user1.id, "BTC", {"operator": "above", "price": 100.0})

    assert await count_active_alerts(db_session, user1.id) == 1
    assert await count_active_alerts(db_session, user2.id) == 0


async def test_list_active_price_alerts_with_users(db_session) -> None:
    user = await _make_user(db_session, 5)
    await create_price_alert(db_session, user.id, "BTC", {"operator": "above", "price": 100.0})

    rows = await list_active_price_alerts_with_users(db_session)
    assert len(rows) == 1
    alert, owner = rows[0]
    assert alert.symbol == "BTC"
    assert owner.id == user.id
    assert owner.telegram_id == 5
