from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.ai.accuracy import cache_accuracy_report, compute_accuracy_report
from app.ai.models import Prediction, PredictionDirection, PredictionOutcome, PredictionSource
from app.ai.models import RiskLevel as PredictionRiskLevel
from app.core.redis import get_redis
from app.db.session import get_session
from app.main import app


def _prediction() -> Prediction:
    return Prediction(
        user_id=None,
        symbol="BTCUSDT@binance",
        tf="1h",
        direction=PredictionDirection.LONG,
        confidence=65.0,
        entry_low=95.0,
        entry_high=100.0,
        targets=[110.0, 120.0],
        invalidation=90.0,
        risk_level=PredictionRiskLevel.MEDIUM,
        factors={},
        source=PredictionSource.CHAT,
        model_version="fake-model",
        created_at=datetime.now(UTC),
        outcome=PredictionOutcome.TP1_REACHED,
    )


async def test_accuracy_endpoint_returns_cache_when_present(fake_redis, db_session) -> None:
    db_session.add(_prediction())
    await db_session.commit()
    report = await compute_accuracy_report(db_session)
    await cache_accuracy_report(fake_redis, report)

    app.dependency_overrides[get_redis] = lambda: fake_redis
    try:
        client = TestClient(app)
        response = client.get("/webapp/accuracy")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["total_predictions"] == 1
    assert body["win_rate"] == 100.0


async def test_accuracy_endpoint_falls_back_to_live_compute_on_cache_miss(fake_redis, db_session) -> None:
    db_session.add(_prediction())
    await db_session.commit()

    async def fake_session():
        yield db_session

    app.dependency_overrides[get_redis] = lambda: fake_redis
    app.dependency_overrides[get_session] = fake_session
    try:
        client = TestClient(app)
        response = client.get("/webapp/accuracy")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["total_predictions"] == 1
