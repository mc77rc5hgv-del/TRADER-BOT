import enum
from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TradingStyle(str, enum.Enum):
    SCALPING = "scalping"
    INTRADAY = "intraday"
    SWING = "swing"
    INVESTING = "investing"


class RiskProfile(str, enum.Enum):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


class PreferredMarket(str, enum.Enum):
    BTC = "btc"
    ALTS = "alts"
    BOTH = "both"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    locale: Mapped[str] = mapped_column(String(10), default="ru", server_default="ru")

    trading_style: Mapped[TradingStyle | None] = mapped_column(
        Enum(TradingStyle, name="trading_style"), nullable=True
    )
    risk_profile: Mapped[RiskProfile | None] = mapped_column(
        Enum(RiskProfile, name="risk_profile"), nullable=True
    )
    preferred_markets: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Bumped on every get_or_create_user() call (app/bot/repository.py) - the
    # only per-request signal cheap enough to update on nearly every bot/
    # webapp interaction. Backs the DAU/WAU figures in TZ section 11.
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    watchlist_items: Mapped[list["WatchlistItem"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class WatchlistItem(Base):
    __tablename__ = "watchlist"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="watchlist_items")
