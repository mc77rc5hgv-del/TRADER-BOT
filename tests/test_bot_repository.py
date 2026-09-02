from datetime import UTC, datetime, timedelta

from app.bot.repository import get_or_create_user


async def test_get_or_create_user_creates_new_user(db_session) -> None:
    user = await get_or_create_user(db_session, telegram_id=123, username="alice")

    assert user.telegram_id == 123
    assert user.username == "alice"
    assert user.last_active_at is not None


async def test_get_or_create_user_bumps_last_active_at_on_repeat_calls(db_session) -> None:
    user = await get_or_create_user(db_session, telegram_id=123, username="alice")
    stale_time = datetime.now(UTC) - timedelta(days=5)
    user.last_active_at = stale_time
    await db_session.commit()

    updated = await get_or_create_user(db_session, telegram_id=123, username="alice")

    assert updated.last_active_at > stale_time


async def test_get_or_create_user_updates_changed_username(db_session) -> None:
    await get_or_create_user(db_session, telegram_id=123, username="alice")

    updated = await get_or_create_user(db_session, telegram_id=123, username="alice_new")

    assert updated.username == "alice_new"
