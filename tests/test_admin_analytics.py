from datetime import UTC, datetime, timedelta

from app.admin.analytics import (
    compute_activity_report,
    compute_conversion_report,
    compute_cost_report,
)
from app.ai.models import AIRequest
from app.billing.models import Subscription, SubscriptionStatus, SubscriptionTier
from app.users.models import User


async def _make_user(db_session, telegram_id: int, last_active_at: datetime | None = None) -> User:
    user = User(telegram_id=telegram_id)
    if last_active_at is not None:
        user.last_active_at = last_active_at
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def _ai_request(user_id: int | None, cost_usd: float, latency_ms: int, created_at: datetime) -> AIRequest:
    return AIRequest(
        user_id=user_id,
        type="chat_analysis",
        tokens_in=100,
        tokens_out=50,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
        model="fake-model",
        created_at=created_at,
    )


async def test_cost_report_empty(db_session) -> None:
    report = await compute_cost_report(db_session)

    assert report.total_cost_usd == 0.0
    assert report.total_requests == 0
    assert report.by_day == []
    assert report.top_users == []
    assert report.latency_p50_ms is None


async def test_cost_report_aggregates_by_day_and_user(db_session) -> None:
    now = datetime.now(UTC)
    user_a = await _make_user(db_session, 1)
    user_b = await _make_user(db_session, 2)

    db_session.add_all(
        [
            _ai_request(user_a.id, cost_usd=1.0, latency_ms=100, created_at=now),
            _ai_request(user_a.id, cost_usd=2.0, latency_ms=200, created_at=now),
            _ai_request(user_b.id, cost_usd=0.5, latency_ms=300, created_at=now),
            _ai_request(None, cost_usd=0.25, latency_ms=50, created_at=now),  # scanner, no user
            _ai_request(user_b.id, cost_usd=5.0, latency_ms=999, created_at=now - timedelta(days=60)),  # too old
        ]
    )
    await db_session.commit()

    report = await compute_cost_report(db_session)

    assert report.total_requests == 4
    assert report.total_cost_usd == 3.75
    assert len(report.by_day) == 1
    assert report.by_day[0].requests == 4

    top_by_user = {row.user_id: row.cost_usd for row in report.top_users}
    assert top_by_user[user_a.id] == 3.0
    assert top_by_user[user_b.id] == 0.5
    assert report.top_users[0].user_id == user_a.id  # sorted by cost desc

    assert report.latency_p50_ms is not None
    assert report.latency_p95_ms is not None


async def test_cost_report_top_n_limits_results(db_session) -> None:
    now = datetime.now(UTC)
    users = [await _make_user(db_session, i) for i in range(100, 105)]
    db_session.add_all([_ai_request(u.id, cost_usd=1.0, latency_ms=10, created_at=now) for u in users])
    await db_session.commit()

    report = await compute_cost_report(db_session, top_n=2)

    assert len(report.top_users) == 2


async def test_activity_report_counts_recent_users(db_session) -> None:
    now = datetime.now(UTC)
    await _make_user(db_session, 1, last_active_at=now)  # active today -> dau + wau
    await _make_user(db_session, 2, last_active_at=now - timedelta(days=3))  # wau only
    await _make_user(db_session, 3, last_active_at=now - timedelta(days=30))  # neither

    report = await compute_activity_report(db_session)

    assert report.dau == 1
    assert report.wau == 2


async def test_conversion_report_counts_active_pro_and_conversion_rate(db_session) -> None:
    now = datetime.now(UTC)
    pro_user = await _make_user(db_session, 1)
    free_user = await _make_user(db_session, 2)

    db_session.add(
        Subscription(
            user_id=pro_user.id,
            tier=SubscriptionTier.PRO,
            status=SubscriptionStatus.ACTIVE,
            started_at=now,
            expires_at=now + timedelta(days=30),
        )
    )
    await db_session.commit()

    report = await compute_conversion_report(db_session)

    assert report.total_users == 2
    assert report.active_pro_users == 1
    assert report.conversion_rate == 50.0
    assert free_user.id  # sanity: second user exists and isn't PRO


async def test_conversion_report_counts_recently_lapsed_as_churn(db_session) -> None:
    now = datetime.now(UTC)
    lapsed_user = await _make_user(db_session, 1)
    renewed_user = await _make_user(db_session, 2)
    long_ago_user = await _make_user(db_session, 3)

    db_session.add_all(
        [
            # lapsed 5 days ago, never renewed -> counts as churn
            Subscription(
                user_id=lapsed_user.id,
                tier=SubscriptionTier.PRO,
                status=SubscriptionStatus.ACTIVE,
                started_at=now - timedelta(days=35),
                expires_at=now - timedelta(days=5),
            ),
            # lapsed then renewed -> latest row is active, not churn
            Subscription(
                user_id=renewed_user.id,
                tier=SubscriptionTier.PRO,
                status=SubscriptionStatus.ACTIVE,
                started_at=now - timedelta(days=65),
                expires_at=now - timedelta(days=35),
            ),
            Subscription(
                user_id=renewed_user.id,
                tier=SubscriptionTier.PRO,
                status=SubscriptionStatus.ACTIVE,
                started_at=now - timedelta(days=3),
                expires_at=now + timedelta(days=27),
            ),
            # lapsed 90 days ago -> outside the 30-day churn window
            Subscription(
                user_id=long_ago_user.id,
                tier=SubscriptionTier.PRO,
                status=SubscriptionStatus.ACTIVE,
                started_at=now - timedelta(days=120),
                expires_at=now - timedelta(days=90),
            ),
        ]
    )
    await db_session.commit()

    report = await compute_conversion_report(db_session, churn_window_days=30)

    assert report.active_pro_users == 1  # renewed_user only
    assert report.churned_in_window == 1  # lapsed_user only
