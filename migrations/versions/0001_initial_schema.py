"""initial schema: users, watchlist, subscriptions, alerts, predictions, ai_requests, screenshots

Revision ID: 0001
Revises:
Create Date: 2026-09-02

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("locale", sa.String(length=10), nullable=False, server_default="ru"),
        sa.Column(
            "trading_style",
            sa.Enum("scalping", "intraday", "swing", "investing", name="trading_style"),
            nullable=True,
        ),
        sa.Column(
            "risk_profile",
            sa.Enum("conservative", "balanced", "aggressive", name="risk_profile"),
            nullable=True,
        ),
        sa.Column("preferred_markets", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)

    op.create_table(
        "watchlist",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_watchlist_user_id", "watchlist", ["user_id"])

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tier",
            sa.Enum("free", "pro", name="subscription_tier"),
            nullable=False,
            server_default="free",
        ),
        sa.Column(
            "status",
            sa.Enum("active", "expired", "canceled", name="subscription_status"),
            nullable=False,
            server_default="active",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payment_provider", sa.String(length=50), nullable=True),
        sa.Column("external_payment_id", sa.String(length=255), nullable=True),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column(
            "type", sa.Enum("price", "rsi", "breakout", name="alert_type"), nullable=False
        ),
        sa.Column("condition", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("active", "triggered", "expired", name="alert_status"),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "delivery_mode",
            sa.Enum(
                "normal", "important_only", "critical_only", name="alert_delivery_mode"
            ),
            nullable=False,
            server_default="normal",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_alerts_user_id", "alerts", ["user_id"])

    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("tf", sa.String(length=8), nullable=False),
        sa.Column(
            "direction",
            sa.Enum("long", "short", "neutral", name="prediction_direction"),
            nullable=False,
        ),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("entry_low", sa.Float(), nullable=False),
        sa.Column("entry_high", sa.Float(), nullable=False),
        sa.Column("targets", sa.JSON(), nullable=False),
        sa.Column("invalidation", sa.Float(), nullable=False),
        sa.Column(
            "risk_level",
            sa.Enum("low", "medium", "high", name="prediction_risk_level"),
            nullable=False,
        ),
        sa.Column("factors", sa.JSON(), nullable=False),
        sa.Column(
            "source",
            sa.Enum("chat", "screenshot", "scanner", name="prediction_source"),
            nullable=False,
        ),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column(
            "outcome",
            sa.Enum(
                "tp1_reached",
                "tp2_reached",
                "stop_hit",
                "expired_no_hit",
                name="prediction_outcome",
            ),
            nullable=True,
        ),
        sa.Column("outcome_evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_predictions_user_id", "predictions", ["user_id"])
    op.create_index("ix_predictions_symbol", "predictions", ["symbol"])

    op.create_table(
        "ai_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("tokens_in", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens_out", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_ai_requests_user_id", "ai_requests", ["user_id"])

    op.create_table(
        "screenshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_screenshots_user_id", "screenshots", ["user_id"])


def downgrade() -> None:
    op.drop_table("screenshots")
    op.drop_table("ai_requests")
    op.drop_table("predictions")
    op.drop_table("alerts")
    op.drop_table("subscriptions")
    op.drop_table("watchlist")
    op.drop_table("users")

    bind = op.get_bind()
    for enum_name in (
        "prediction_outcome",
        "prediction_source",
        "prediction_risk_level",
        "prediction_direction",
        "alert_delivery_mode",
        "alert_status",
        "alert_type",
        "subscription_status",
        "subscription_tier",
        "risk_profile",
        "trading_style",
    ):
        sa.Enum(name=enum_name).drop(bind, checkfirst=True)
