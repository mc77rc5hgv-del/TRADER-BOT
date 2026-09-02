import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    event,
    func,
    inspect,
)
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.db.base import Base, enum_values


class PredictionDirection(str, enum.Enum):
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PredictionSource(str, enum.Enum):
    CHAT = "chat"
    SCREENSHOT = "screenshot"
    SCANNER = "scanner"


class PredictionOutcome(str, enum.Enum):
    TP1_REACHED = "tp1_reached"
    TP2_REACHED = "tp2_reached"
    STOP_HIT = "stop_hit"
    EXPIRED_NO_HIT = "expired_no_hit"


# Fields that must never change after creation (TZ section 6.3). `outcome` and
# `outcome_evaluated_at` are the only columns the nightly evaluation job may set.
_IMMUTABLE_FIELDS = {
    "confidence",
    "entry_low",
    "entry_high",
    "targets",
    "invalidation",
    "direction",
    "factors",
}


class Prediction(Base):
    """Prediction Ledger: an immutable record of every AI forecast, used to
    calibrate confidence against real outcomes (TZ sections 6.3, 6.6)."""

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    tf: Mapped[str] = mapped_column(String(8), nullable=False)

    direction: Mapped[PredictionDirection] = mapped_column(
        Enum(PredictionDirection, name="prediction_direction", values_callable=enum_values)
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    entry_low: Mapped[float] = mapped_column(Float, nullable=False)
    entry_high: Mapped[float] = mapped_column(Float, nullable=False)
    targets: Mapped[list[float]] = mapped_column(JSON, nullable=False)
    invalidation: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, name="prediction_risk_level", values_callable=enum_values)
    )
    factors: Mapped[dict] = mapped_column(JSON, nullable=False)
    source: Mapped[PredictionSource] = mapped_column(
        Enum(PredictionSource, name="prediction_source", values_callable=enum_values)
    )
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)

    outcome: Mapped[PredictionOutcome | None] = mapped_column(
        Enum(PredictionOutcome, name="prediction_outcome", values_callable=enum_values),
        nullable=True,
    )
    outcome_evaluated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


@event.listens_for(Session, "before_flush")
def _enforce_prediction_immutability(session: Session, flush_context, instances) -> None:
    for obj in session.dirty:
        if not isinstance(obj, Prediction):
            continue
        insp = inspect(obj)
        if insp.pending:
            continue
        for field in _IMMUTABLE_FIELDS:
            if insp.attrs[field].history.has_changes():
                raise ValueError(
                    f"Prediction.{field} is immutable and cannot be modified after creation"
                )


class AIRequest(Base):
    """Per-request cost/latency accounting, used for the internal cost/DAU
    dashboard (TZ section 11)."""

    __tablename__ = "ai_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    tokens_out: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    cost_usd: Mapped[float] = mapped_column(Float, default=0, server_default="0")
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Screenshot(Base):
    """Uploaded chart screenshots. Retained only for a limited TTL (TZ section 6.4);
    deletion is handled by a separate cleanup job, not by this model."""

    __tablename__ = "screenshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
