from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.ai.accuracy import (
    EXPIRY_CANDLE_HORIZON,
    cache_accuracy_report,
    compute_accuracy_report,
    evaluate_prediction,
    get_cached_accuracy_report,
    run_evaluation,
)
from app.ai.models import Prediction, PredictionDirection, PredictionOutcome, PredictionSource
from app.ai.models import RiskLevel as PredictionRiskLevel
from app.market.schemas import Candle, Ticker
from app.market.service import MarketDataEngine

CREATED_AT = datetime(2024, 1, 1, tzinfo=UTC)


def _candle(hours_after_creation: int, high: float, low: float) -> Candle:
    open_time = CREATED_AT + timedelta(hours=hours_after_creation)
    mid = (high + low) / 2
    return Candle(
        open_time=open_time,
        open=mid,
        high=high,
        low=low,
        close=mid,
        volume=1.0,
        close_time=open_time + timedelta(hours=1),
    )


class FakeBinanceClient:
    def __init__(self, candles: list[Candle]) -> None:
        self.candles = candles

    async def get_klines(self, symbol, interval, limit=200):
        return self.candles

    async def get_ticker_24hr(self, symbol):
        return Ticker(symbol=symbol, price=100.0, price_change_percent_24h=0.0)


def _make_prediction(
    direction: PredictionDirection = PredictionDirection.LONG,
    entry_low: float = 95.0,
    entry_high: float = 100.0,
    target1: float = 110.0,
    target2: float = 120.0,
    invalidation: float = 90.0,
    symbol: str = "BTCUSDT@binance",
    tf: str = "1h",
    created_at: datetime = CREATED_AT,
    outcome: PredictionOutcome | None = None,
) -> Prediction:
    return Prediction(
        user_id=None,
        symbol=symbol,
        tf=tf,
        direction=direction,
        confidence=65.0,
        entry_low=entry_low,
        entry_high=entry_high,
        targets=[target1, target2],
        invalidation=invalidation,
        risk_level=PredictionRiskLevel.MEDIUM,
        factors={},
        source=PredictionSource.CHAT,
        model_version="fake-model",
        created_at=created_at,
        outcome=outcome,
    )


async def test_long_tp1_hit_before_stop(fake_redis) -> None:
    candles = [_candle(1, high=112.0, low=99.0)]
    engine = MarketDataEngine(FakeBinanceClient(candles), fake_redis)
    prediction = _make_prediction()

    outcome = await evaluate_prediction(prediction, engine)

    assert outcome == PredictionOutcome.TP1_REACHED


async def test_long_tp2_hit_directly(fake_redis) -> None:
    candles = [_candle(1, high=125.0, low=99.0)]
    engine = MarketDataEngine(FakeBinanceClient(candles), fake_redis)
    prediction = _make_prediction()

    outcome = await evaluate_prediction(prediction, engine)

    assert outcome == PredictionOutcome.TP2_REACHED


async def test_long_stop_hit_before_target(fake_redis) -> None:
    candles = [_candle(1, high=101.0, low=88.0)]
    engine = MarketDataEngine(FakeBinanceClient(candles), fake_redis)
    prediction = _make_prediction()

    outcome = await evaluate_prediction(prediction, engine)

    assert outcome == PredictionOutcome.STOP_HIT


async def test_candle_touching_both_levels_scores_conservative_stop(fake_redis) -> None:
    # one candle whose range spans both TP1 and the stop - can't know which
    # was touched first from OHLC alone, so the conservative read (stop) wins
    candles = [_candle(1, high=115.0, low=85.0)]
    engine = MarketDataEngine(FakeBinanceClient(candles), fake_redis)
    prediction = _make_prediction()

    outcome = await evaluate_prediction(prediction, engine)

    assert outcome == PredictionOutcome.STOP_HIT


async def test_short_direction_uses_inverted_levels(fake_redis) -> None:
    candles = [_candle(1, high=101.0, low=88.0)]
    engine = MarketDataEngine(FakeBinanceClient(candles), fake_redis)
    prediction = _make_prediction(
        direction=PredictionDirection.SHORT,
        entry_low=100.0,
        entry_high=105.0,
        target1=90.0,
        target2=80.0,
        invalidation=110.0,
    )

    outcome = await evaluate_prediction(prediction, engine)

    assert outcome == PredictionOutcome.TP1_REACHED


async def test_no_hit_yet_stays_pending(fake_redis) -> None:
    candles = [_candle(1, high=101.0, low=99.0)]
    engine = MarketDataEngine(FakeBinanceClient(candles), fake_redis)
    prediction = _make_prediction()

    outcome = await evaluate_prediction(prediction, engine)

    assert outcome is None


async def test_expires_after_horizon_with_no_hit(fake_redis) -> None:
    candles = [_candle(h, high=101.0, low=99.0) for h in range(EXPIRY_CANDLE_HORIZON + 5)]
    engine = MarketDataEngine(FakeBinanceClient(candles), fake_redis)
    prediction = _make_prediction()

    outcome = await evaluate_prediction(prediction, engine)

    assert outcome == PredictionOutcome.EXPIRED_NO_HIT


async def test_run_evaluation_updates_pending_predictions_only(fake_redis, db_session) -> None:
    candles = [_candle(1, high=112.0, low=99.0)]
    engine = MarketDataEngine(FakeBinanceClient(candles), fake_redis)

    resolved = _make_prediction()
    resolved.outcome = PredictionOutcome.TP1_REACHED
    pending = _make_prediction()
    neutral = _make_prediction(direction=PredictionDirection.NEUTRAL)

    db_session.add_all([resolved, pending, neutral])
    await db_session.commit()

    updated = await run_evaluation(db_session, engine)

    assert updated == 1
    predictions = (await db_session.execute(select(Prediction))).scalars().all()
    by_id = {p.id: p for p in predictions}
    assert by_id[pending.id].outcome == PredictionOutcome.TP1_REACHED
    assert by_id[pending.id].outcome_evaluated_at is not None
    assert by_id[neutral.id].outcome is None


async def test_compute_accuracy_report_aggregates_resolved_predictions(db_session) -> None:
    now = datetime.now(UTC)
    db_session.add_all(
        [
            _make_prediction(
                symbol="BTCUSDT@binance",
                tf="1h",
                created_at=now,
                outcome=PredictionOutcome.TP1_REACHED,
            ),
            _make_prediction(
                symbol="BTCUSDT@binance",
                tf="1h",
                created_at=now,
                outcome=PredictionOutcome.STOP_HIT,
            ),
            _make_prediction(
                symbol="ETHUSDT@binance",
                tf="4h",
                created_at=now,
                outcome=PredictionOutcome.TP2_REACHED,
            ),
            _make_prediction(
                symbol="ETHUSDT@binance", tf="4h", created_at=now, outcome=None
            ),  # still pending
            _make_prediction(direction=PredictionDirection.NEUTRAL, created_at=now),  # excluded
            _make_prediction(
                created_at=now - timedelta(days=60), outcome=PredictionOutcome.TP1_REACHED
            ),  # too old
        ]
    )
    await db_session.commit()

    report = await compute_accuracy_report(db_session)

    assert report.total_predictions == 4
    assert report.resolved_predictions == 3
    assert report.win_rate == pytest.approx(200 / 3)  # 2 wins out of 3 resolved
    assert report.avg_realized_r == pytest.approx((1.5 - 1.0 + 3.0) / 3)

    by_symbol = {row.key: row for row in report.by_symbol}
    assert by_symbol["BTCUSDT@binance"].total_predictions == 2
    assert by_symbol["BTCUSDT@binance"].win_rate == pytest.approx(50.0)
    assert by_symbol["ETHUSDT@binance"].total_predictions == 2
    assert by_symbol["ETHUSDT@binance"].win_rate == pytest.approx(100.0)

    by_tf = {row.key: row for row in report.by_tf}
    assert by_tf["1h"].total_predictions == 2
    assert by_tf["4h"].total_predictions == 2


async def test_compute_accuracy_report_empty_has_none_rates(db_session) -> None:
    report = await compute_accuracy_report(db_session)

    assert report.total_predictions == 0
    assert report.win_rate is None
    assert report.avg_realized_r is None
    assert report.by_symbol == []


async def test_accuracy_report_cache_round_trip(fake_redis, db_session) -> None:
    assert await get_cached_accuracy_report(fake_redis) is None

    db_session.add(
        _make_prediction(created_at=datetime.now(UTC), outcome=PredictionOutcome.TP1_REACHED)
    )
    await db_session.commit()
    report = await compute_accuracy_report(db_session)

    await cache_accuracy_report(fake_redis, report)
    cached = await get_cached_accuracy_report(fake_redis)

    assert cached is not None
    assert cached.total_predictions == 1
    assert cached.win_rate == pytest.approx(100.0)
