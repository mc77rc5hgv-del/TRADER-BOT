from datetime import UTC, datetime, timedelta

from app.billing.models import Subscription, SubscriptionStatus, SubscriptionTier
from app.billing.service import (
    TIER_LIMITS,
    activate_pro_subscription,
    get_active_subscription,
    get_active_tier,
    get_tier_limits,
)
from app.users.models import User


async def _make_user(db_session, telegram_id: int) -> User:
    user = User(telegram_id=telegram_id)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def test_user_without_subscription_is_free(db_session) -> None:
    user = await _make_user(db_session, 1)
    assert await get_active_tier(db_session, user.id) == SubscriptionTier.FREE


async def test_active_pro_subscription_is_pro(db_session) -> None:
    user = await _make_user(db_session, 2)
    await activate_pro_subscription(db_session, user.id, "telegram_stars", "charge_1")

    assert await get_active_tier(db_session, user.id) == SubscriptionTier.PRO


async def test_expired_subscription_falls_back_to_free(db_session) -> None:
    user = await _make_user(db_session, 3)
    db_session.add(
        Subscription(
            user_id=user.id,
            tier=SubscriptionTier.PRO,
            status=SubscriptionStatus.ACTIVE,
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )
    )
    await db_session.commit()

    assert await get_active_tier(db_session, user.id) == SubscriptionTier.FREE


async def test_canceled_subscription_falls_back_to_free(db_session) -> None:
    user = await _make_user(db_session, 4)
    db_session.add(
        Subscription(
            user_id=user.id,
            tier=SubscriptionTier.PRO,
            status=SubscriptionStatus.CANCELED,
            expires_at=datetime.now(UTC) + timedelta(days=10),
        )
    )
    await db_session.commit()

    assert await get_active_tier(db_session, user.id) == SubscriptionTier.FREE


async def test_get_tier_limits_matches_tier(db_session) -> None:
    user = await _make_user(db_session, 5)
    assert await get_tier_limits(db_session, user.id) == TIER_LIMITS[SubscriptionTier.FREE]

    await activate_pro_subscription(db_session, user.id, "telegram_stars", "charge_2")
    assert await get_tier_limits(db_session, user.id) == TIER_LIMITS[SubscriptionTier.PRO]


async def test_get_active_subscription_returns_none_for_free_user(db_session) -> None:
    user = await _make_user(db_session, 7)
    assert await get_active_subscription(db_session, user.id) is None


async def test_get_active_subscription_returns_row_for_pro_user(db_session) -> None:
    user = await _make_user(db_session, 8)
    created = await activate_pro_subscription(db_session, user.id, "telegram_stars", "charge_4")

    subscription = await get_active_subscription(db_session, user.id)

    assert subscription is not None
    assert subscription.id == created.id


async def test_activate_pro_subscription_sets_expiry(db_session) -> None:
    user = await _make_user(db_session, 6)
    before = datetime.now(UTC)
    subscription = await activate_pro_subscription(
        db_session, user.id, "telegram_stars", "charge_3"
    )

    assert subscription.expires_at is not None
    expires_at = subscription.expires_at
    if expires_at.tzinfo is None:  # SQLite doesn't round-trip tzinfo, see billing/service.py
        expires_at = expires_at.replace(tzinfo=UTC)
    assert expires_at > before + timedelta(days=29)
    assert subscription.payment_provider == "telegram_stars"
    assert subscription.external_payment_id == "charge_3"
