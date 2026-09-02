"""Subscription tier resolution and per-tier limits (TZ section 8)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.models import Subscription, SubscriptionStatus, SubscriptionTier

PRO_SUBSCRIPTION_DURATION_DAYS = 30

# Telegram Stars price for one PRO period. Stars have no fixed USD rate;
# this is a starting guess (TZ section 82: "$9-15/month equivalent"), meant
# to be tuned once real conversion data exists.
PRO_PRICE_STARS = 300


@dataclass(frozen=True)
class TierLimits:
    ai_analyses_per_day: int
    max_active_alerts: int


TIER_LIMITS: dict[SubscriptionTier, TierLimits] = {
    SubscriptionTier.FREE: TierLimits(ai_analyses_per_day=5, max_active_alerts=3),
    SubscriptionTier.PRO: TierLimits(ai_analyses_per_day=50, max_active_alerts=20),
}


async def get_active_subscription(session: AsyncSession, user_id: int) -> Subscription | None:
    """The user's current ACTIVE, non-expired subscription row, or None if
    they're on FREE (no row, an expired row, or a non-ACTIVE row)."""
    result = await session.execute(
        select(Subscription)
        .where(Subscription.user_id == user_id, Subscription.status == SubscriptionStatus.ACTIVE)
        .order_by(Subscription.started_at.desc())
    )
    subscription = result.scalars().first()
    if subscription is None:
        return None

    expires_at = subscription.expires_at
    if expires_at is not None:
        # SQLite (used in tests) doesn't round-trip tzinfo through
        # DateTime(timezone=True) the way Postgres does - values written as
        # UTC come back naive. Everything this module writes is UTC, so a
        # naive value read back is UTC too.
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at < datetime.now(UTC):
            return None

    return subscription


async def get_active_tier(session: AsyncSession, user_id: int) -> SubscriptionTier:
    """FREE unless there's a non-expired ACTIVE subscription row — no row
    at all (the common case pre-billing) means FREE, same as an expired one."""
    subscription = await get_active_subscription(session, user_id)
    return subscription.tier if subscription is not None else SubscriptionTier.FREE


async def get_tier_limits(session: AsyncSession, user_id: int) -> TierLimits:
    tier = await get_active_tier(session, user_id)
    return TIER_LIMITS[tier]


async def activate_pro_subscription(
    session: AsyncSession,
    user_id: int,
    payment_provider: str,
    external_payment_id: str,
    duration_days: int = PRO_SUBSCRIPTION_DURATION_DAYS,
) -> Subscription:
    """Records a purchase as a new row rather than mutating an existing one
    — cheap purchase history, and get_active_tier() only ever needs the
    latest non-expired row."""
    now = datetime.now(UTC)
    subscription = Subscription(
        user_id=user_id,
        tier=SubscriptionTier.PRO,
        status=SubscriptionStatus.ACTIVE,
        started_at=now,
        expires_at=now + timedelta(days=duration_days),
        payment_provider=payment_provider,
        external_payment_id=external_payment_id,
    )
    session.add(subscription)
    await session.commit()
    await session.refresh(subscription)
    return subscription
