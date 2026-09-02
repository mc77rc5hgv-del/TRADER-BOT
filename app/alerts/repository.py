from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.alerts.models import Alert, AlertStatus, AlertType
from app.users.models import User


async def count_active_alerts(session: AsyncSession, user_id: int) -> int:
    result = await session.execute(
        select(func.count()).select_from(Alert).where(Alert.user_id == user_id, Alert.status == AlertStatus.ACTIVE)
    )
    return result.scalar_one()


async def list_active_alerts_for_user(session: AsyncSession, user_id: int) -> list[Alert]:
    result = await session.execute(
        select(Alert)
        .where(Alert.user_id == user_id, Alert.status == AlertStatus.ACTIVE)
        .order_by(Alert.created_at)
    )
    return list(result.scalars().all())


async def create_price_alert(
    session: AsyncSession, user_id: int, symbol: str, condition: dict
) -> Alert:
    alert = Alert(user_id=user_id, symbol=symbol, type=AlertType.PRICE, condition=condition)
    session.add(alert)
    await session.commit()
    await session.refresh(alert)
    return alert


async def list_active_price_alerts_with_users(session: AsyncSession) -> list[tuple[Alert, User]]:
    """Used by the delivery worker — needs each alert's owner's telegram_id."""
    result = await session.execute(
        select(Alert, User)
        .join(User, Alert.user_id == User.id)
        .where(Alert.status == AlertStatus.ACTIVE, Alert.type == AlertType.PRICE)
    )
    return list(result.all())
