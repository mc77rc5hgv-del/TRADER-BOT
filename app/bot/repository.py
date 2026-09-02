from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.users.models import PreferredMarket, RiskProfile, TradingStyle, User


async def get_or_create_user(session: AsyncSession, telegram_id: int, username: str | None) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user is not None:
        if username and user.username != username:
            user.username = username
            await session.commit()
        return user

    user = User(telegram_id=telegram_id, username=username)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def set_trading_style(session: AsyncSession, user: User, style: TradingStyle) -> None:
    user.trading_style = style
    await session.commit()


async def set_risk_profile(session: AsyncSession, user: User, risk: RiskProfile) -> None:
    user.risk_profile = risk
    await session.commit()


async def set_preferred_markets(session: AsyncSession, user: User, market: PreferredMarket) -> None:
    user.preferred_markets = [market.value]
    await session.commit()
