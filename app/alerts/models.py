import enum
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AlertType(str, enum.Enum):
    PRICE = "price"
    RSI = "rsi"
    BREAKOUT = "breakout"


class AlertStatus(str, enum.Enum):
    ACTIVE = "active"
    TRIGGERED = "triggered"
    EXPIRED = "expired"


class DeliveryMode(str, enum.Enum):
    NORMAL = "normal"
    IMPORTANT_ONLY = "important_only"
    CRITICAL_ONLY = "critical_only"


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    type: Mapped[AlertType] = mapped_column(Enum(AlertType, name="alert_type"))
    condition: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[AlertStatus] = mapped_column(
        Enum(AlertStatus, name="alert_status"),
        default=AlertStatus.ACTIVE,
        server_default=AlertStatus.ACTIVE.value,
    )
    delivery_mode: Mapped[DeliveryMode] = mapped_column(
        Enum(DeliveryMode, name="alert_delivery_mode"),
        default=DeliveryMode.NORMAL,
        server_default=DeliveryMode.NORMAL.value,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
