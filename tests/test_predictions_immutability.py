import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.models import (
    Prediction,
    PredictionDirection,
    PredictionOutcome,
    PredictionSource,
    RiskLevel,
)


def _make_prediction() -> Prediction:
    return Prediction(
        symbol="BTCUSDT@binance",
        tf="4h",
        direction=PredictionDirection.LONG,
        confidence=64.0,
        entry_low=111800,
        entry_high=112300,
        targets=[113600, 114900, 116200],
        invalidation=110950,
        risk_level=RiskLevel.MEDIUM,
        factors={"market_structure": 15, "momentum": 7},
        source=PredictionSource.CHAT,
        model_version="v0",
    )


async def test_prediction_can_be_created(db_session: AsyncSession) -> None:
    prediction = _make_prediction()
    db_session.add(prediction)
    await db_session.commit()
    assert prediction.id is not None


async def test_outcome_can_be_updated_after_creation(db_session: AsyncSession) -> None:
    prediction = _make_prediction()
    db_session.add(prediction)
    await db_session.commit()

    prediction.outcome = PredictionOutcome.TP1_REACHED
    await db_session.commit()
    assert prediction.outcome == PredictionOutcome.TP1_REACHED


async def test_confidence_cannot_be_modified_after_creation(db_session: AsyncSession) -> None:
    prediction = _make_prediction()
    db_session.add(prediction)
    await db_session.commit()

    prediction.confidence = 99.0
    with pytest.raises(ValueError, match="immutable"):
        await db_session.commit()


async def test_targets_cannot_be_modified_after_creation(db_session: AsyncSession) -> None:
    prediction = _make_prediction()
    db_session.add(prediction)
    await db_session.commit()

    prediction.targets = [999999]
    with pytest.raises(ValueError, match="immutable"):
        await db_session.commit()
