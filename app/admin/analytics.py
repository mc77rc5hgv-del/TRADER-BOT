"""Internal cost/DAU/conversion analytics (TZ section 11) — the minimum
admin visibility the TZ requires before a proper dashboard exists ("доступен
хотя бы как внутренний SQL-дашборд/скрипт"). No web UI; see
app/admin/report_cli.py for the script entrypoint."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.models import AIRequest
from app.billing.models import Subscription, SubscriptionStatus, SubscriptionTier
from app.users.models import User

DEFAULT_COST_WINDOW_DAYS = 30
DEFAULT_CHURN_WINDOW_DAYS = 30
DEFAULT_TOP_USERS = 10


@dataclass(frozen=True)
class DailyCost:
    day: str  # ISO date
    cost_usd: float
    requests: int


@dataclass(frozen=True)
class UserCost:
    user_id: int
    cost_usd: float
    requests: int


@dataclass(frozen=True)
class CostReport:
    window_days: int
    total_cost_usd: float
    total_requests: int
    by_day: list[DailyCost] = field(default_factory=list)
    top_users: list[UserCost] = field(default_factory=list)
    latency_p50_ms: float | None = None
    latency_p95_ms: float | None = None


@dataclass(frozen=True)
class ActivityReport:
    dau: int
    wau: int


@dataclass(frozen=True)
class ConversionReport:
    total_users: int
    active_pro_users: int
    conversion_rate: float | None  # active_pro_users / total_users * 100
    churned_in_window: int
    churn_window_days: int


def _percentile(sorted_values: list[float], pct: float) -> float | None:
    if not sorted_values:
        return None
    index = min(len(sorted_values) - 1, int(len(sorted_values) * pct))
    return sorted_values[index]


async def compute_cost_report(
    session: AsyncSession, days: int = DEFAULT_COST_WINDOW_DAYS, top_n: int = DEFAULT_TOP_USERS
) -> CostReport:
    since = datetime.now(UTC) - timedelta(days=days)
    result = await session.execute(select(AIRequest).where(AIRequest.created_at >= since))
    requests = result.scalars().all()

    if not requests:
        return CostReport(window_days=days, total_cost_usd=0.0, total_requests=0)

    by_day: dict[str, list[AIRequest]] = {}
    by_user: dict[int, list[AIRequest]] = {}
    for r in requests:
        by_day.setdefault(r.created_at.date().isoformat(), []).append(r)
        if r.user_id is not None:
            by_user.setdefault(r.user_id, []).append(r)

    daily = [
        DailyCost(day=day, cost_usd=sum(r.cost_usd for r in items), requests=len(items))
        for day, items in sorted(by_day.items())
    ]
    top_users = sorted(
        (
            UserCost(user_id=uid, cost_usd=sum(r.cost_usd for r in items), requests=len(items))
            for uid, items in by_user.items()
        ),
        key=lambda u: u.cost_usd,
        reverse=True,
    )[:top_n]
    latencies = sorted(r.latency_ms for r in requests)

    return CostReport(
        window_days=days,
        total_cost_usd=sum(r.cost_usd for r in requests),
        total_requests=len(requests),
        by_day=daily,
        top_users=top_users,
        latency_p50_ms=_percentile(latencies, 0.50),
        latency_p95_ms=_percentile(latencies, 0.95),
    )


async def compute_activity_report(session: AsyncSession) -> ActivityReport:
    """DAU/WAU from User.last_active_at, bumped on every get_or_create_user()
    call (app/bot/repository.py) - the cheapest per-request signal available,
    covering both bot and Mini App traffic."""
    now = datetime.now(UTC)
    dau_count = (
        await session.execute(
            select(func.count())
            .select_from(User)
            .where(User.last_active_at >= now - timedelta(days=1))
        )
    ).scalar_one()
    wau_count = (
        await session.execute(
            select(func.count())
            .select_from(User)
            .where(User.last_active_at >= now - timedelta(days=7))
        )
    ).scalar_one()
    return ActivityReport(dau=dau_count, wau=wau_count)


async def compute_conversion_report(
    session: AsyncSession, churn_window_days: int = DEFAULT_CHURN_WINDOW_DAYS
) -> ConversionReport:
    """Free->Pro conversion and churn, both derived from Subscription.expires_at
    rather than .status - every purchase inserts a new ACTIVE row rather than
    mutating an old one (app.billing.service), so .status never actually
    transitions to EXPIRED/CANCELED in this system; expiry is judged the same
    way app.billing.service.get_active_tier() judges it."""
    total_users = (await session.execute(select(func.count()).select_from(User))).scalar_one()

    result = await session.execute(select(Subscription).order_by(Subscription.started_at))
    latest_by_user: dict[int, Subscription] = {}
    for sub in result.scalars().all():
        latest_by_user[sub.user_id] = sub  # ascending order -> last write per user is the latest

    now = datetime.now(UTC)
    since = now - timedelta(days=churn_window_days)

    active_pro_users = 0
    churned_in_window = 0
    for sub in latest_by_user.values():
        if sub.tier != SubscriptionTier.PRO or sub.status != SubscriptionStatus.ACTIVE:
            continue

        expires_at = sub.expires_at
        if expires_at is not None and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)

        if expires_at is None or expires_at >= now:
            active_pro_users += 1
        elif expires_at >= since:
            # was PRO, lapsed within the window, hasn't purchased since
            churned_in_window += 1

    return ConversionReport(
        total_users=total_users,
        active_pro_users=active_pro_users,
        conversion_rate=(active_pro_users / total_users * 100) if total_users else None,
        churned_in_window=churned_in_window,
        churn_window_days=churn_window_days,
    )
