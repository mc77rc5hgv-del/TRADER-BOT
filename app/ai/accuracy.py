"""Prediction outcome evaluation (TZ sections 6.3, 6.6): a batch job that
checks Prediction Ledger entries against the price action that followed and
records which of TP1/TP2/stop was hit first. Pure price-history comparison —
no LLM call, since nothing here needs judgment, only arithmetic on candles
already fetched through the shared Market Data Engine."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.models import Prediction, PredictionDirection, PredictionOutcome
from app.ai.schemas import AccuracyBreakdownRow, AccuracyReport
from app.market.schemas import Candle
from app.market.service import MarketDataEngine
from app.risk.service import TARGET_R_MULTIPLES

# A prediction with neither its first target nor its invalidation hit after
# this many candles is marked EXPIRED_NO_HIT rather than left pending
# forever. TZ 6.6 doesn't fix an exact horizon; 100 bars is a starting point,
# tunable once real outcome data exists.
EXPIRY_CANDLE_HORIZON = 100

# TZ section 3.6: "статистика ... за последние 30 дней".
REPORT_WINDOW_DAYS = 30

ACCURACY_CACHE_KEY = "accuracy:report"
# The report is refreshed once a day by the same worker that evaluates
# outcomes (TZ 3.6: "обновляется фоновым джобом, не в реальном времени") -
# a generous TTL just guards against a stalled worker serving a report from
# a Redis instance that's since been flushed.
ACCURACY_CACHE_TTL_SECONDS = 2 * 24 * 60 * 60

_RESOLVED_OUTCOMES = (
    PredictionOutcome.TP1_REACHED,
    PredictionOutcome.TP2_REACHED,
    PredictionOutcome.STOP_HIT,
)
_WIN_OUTCOMES = (PredictionOutcome.TP1_REACHED, PredictionOutcome.TP2_REACHED)

# R actually realized per outcome, in units of the initial risk (1R = the
# entry-to-invalidation distance) - the same units app.risk.service sizes
# targets in. EXPIRED_NO_HIT is deliberately excluded elsewhere: it means
# neither level was reached within the evaluation horizon, not a known R.
_REALIZED_R: dict[PredictionOutcome, float] = {
    PredictionOutcome.TP1_REACHED: TARGET_R_MULTIPLES[0],
    PredictionOutcome.TP2_REACHED: TARGET_R_MULTIPLES[1],
    PredictionOutcome.STOP_HIT: -1.0,
}


def _first_hit(
    direction: PredictionDirection,
    candles: list[Candle],
    target1: float,
    target2: float | None,
    invalidation: float,
) -> PredictionOutcome | None:
    """Scans candles in chronological order for whichever level is touched
    first. A candle whose range covers both a target and the invalidation
    level is scored as the stop being hit first — the conservative
    assumption, since candle data alone doesn't say which came first
    intra-candle."""
    for candle in candles:
        if direction == PredictionDirection.LONG:
            stop_touched = candle.low <= invalidation
            tp2_touched = target2 is not None and candle.high >= target2
            tp1_touched = candle.high >= target1
        else:
            stop_touched = candle.high >= invalidation
            tp2_touched = target2 is not None and candle.low <= target2
            tp1_touched = candle.low <= target1

        if stop_touched:
            return PredictionOutcome.STOP_HIT
        if tp2_touched:
            return PredictionOutcome.TP2_REACHED
        if tp1_touched:
            return PredictionOutcome.TP1_REACHED

    return None


async def evaluate_prediction(
    prediction: Prediction, market_engine: MarketDataEngine
) -> PredictionOutcome | None:
    """Returns the outcome to record, or None if it's still too early to
    tell (caller should leave the prediction pending)."""
    market_state = await market_engine.get_market_state(prediction.symbol, prediction.tf)
    if market_state is None:
        return None

    created_at = prediction.created_at
    if created_at.tzinfo is None:
        # SQLite doesn't round-trip tzinfo through DateTime(timezone=True);
        # everything this app writes is UTC, so a naive read-back is UTC too.
        created_at = created_at.replace(tzinfo=UTC)

    candles_since_creation = [c for c in market_state.candles if c.open_time >= created_at]
    if not candles_since_creation:
        return None

    target1 = prediction.targets[0]
    target2 = prediction.targets[1] if len(prediction.targets) > 1 else None
    outcome = _first_hit(
        prediction.direction, candles_since_creation, target1, target2, prediction.invalidation
    )
    if outcome is not None:
        return outcome

    if len(candles_since_creation) >= EXPIRY_CANDLE_HORIZON:
        return PredictionOutcome.EXPIRED_NO_HIT

    return None


async def run_evaluation(db_session: AsyncSession, market_engine: MarketDataEngine) -> int:
    """Evaluates every directional prediction still pending an outcome.
    Returns how many were updated. Predictions.outcome is the one field the
    immutability guard (app.ai.models) allows this job to set."""
    result = await db_session.execute(
        select(Prediction).where(
            Prediction.outcome.is_(None), Prediction.direction != PredictionDirection.NEUTRAL
        )
    )
    predictions = result.scalars().all()

    updated = 0
    for prediction in predictions:
        outcome = await evaluate_prediction(prediction, market_engine)
        if outcome is None:
            continue
        prediction.outcome = outcome
        prediction.outcome_evaluated_at = datetime.now(UTC)
        updated += 1

    if updated:
        await db_session.commit()
    return updated


def _breakdown(
    predictions: Sequence[Prediction], key_fn: Callable[[Prediction], str], top: int | None
) -> list[AccuracyBreakdownRow]:
    groups: dict[str, list[Prediction]] = {}
    for prediction in predictions:
        groups.setdefault(key_fn(prediction), []).append(prediction)

    rows = []
    for key, items in groups.items():
        resolved = [p for p in items if p.outcome in _RESOLVED_OUTCOMES]
        wins = [p for p in resolved if p.outcome in _WIN_OUTCOMES]
        rows.append(
            AccuracyBreakdownRow(
                key=key,
                total_predictions=len(items),
                win_rate=(len(wins) / len(resolved) * 100) if resolved else None,
            )
        )

    rows.sort(key=lambda row: row.total_predictions, reverse=True)
    return rows[:top] if top is not None else rows


async def compute_accuracy_report(
    db_session: AsyncSession, days: int = REPORT_WINDOW_DAYS
) -> AccuracyReport:
    """Aggregates the Prediction Ledger over the last `days` days (TZ 3.6).
    Directionless (neutral) predictions never produce a tradeable setup, so
    they're excluded the same way run_evaluation excludes them."""
    since = datetime.now(UTC) - timedelta(days=days)
    result = await db_session.execute(
        select(Prediction).where(
            Prediction.direction != PredictionDirection.NEUTRAL, Prediction.created_at >= since
        )
    )
    predictions = result.scalars().all()

    resolved = [p for p in predictions if p.outcome in _RESOLVED_OUTCOMES]
    wins = [p for p in resolved if p.outcome in _WIN_OUTCOMES]

    return AccuracyReport(
        window_days=days,
        total_predictions=len(predictions),
        resolved_predictions=len(resolved),
        win_rate=(len(wins) / len(resolved) * 100) if resolved else None,
        avg_realized_r=(sum(_REALIZED_R[p.outcome] for p in resolved) / len(resolved))
        if resolved
        else None,
        by_symbol=_breakdown(predictions, lambda p: p.symbol, top=5),
        by_tf=_breakdown(predictions, lambda p: p.tf, top=None),
    )


async def cache_accuracy_report(redis: Redis, report: AccuracyReport) -> None:
    await redis.set(ACCURACY_CACHE_KEY, report.model_dump_json(), ex=ACCURACY_CACHE_TTL_SECONDS)


async def get_cached_accuracy_report(redis: Redis) -> AccuracyReport | None:
    raw = await redis.get(ACCURACY_CACHE_KEY)
    if raw is None:
        return None
    return AccuracyReport.model_validate_json(raw)
