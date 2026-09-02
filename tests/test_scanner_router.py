from fastapi.testclient import TestClient

from app.core.redis import get_redis
from app.main import app
from app.scanner.schemas import ScannerEntry
from app.scanner.service import cache_scan_results


def _entry(symbol: str, direction: str, confidence: float, risk_level: str) -> ScannerEntry:
    return ScannerEntry(
        symbol=symbol,
        tf="1h",
        direction=direction,
        confidence=confidence,
        risk_reward=1.5,
        risk_level=risk_level,
        price=100.0,
    )


async def test_scanner_endpoint_returns_cached_entries_sorted_by_confidence(fake_redis) -> None:
    await cache_scan_results(
        fake_redis,
        [
            _entry("ETHUSDT@binance", "long", 55.0, "medium"),
            _entry("BTCUSDT@binance", "long", 70.0, "low"),
        ],
    )

    app.dependency_overrides[get_redis] = lambda: fake_redis
    try:
        client = TestClient(app)
        response = client.get("/scanner")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert [e["symbol"] for e in body["entries"]] == ["BTCUSDT@binance", "ETHUSDT@binance"]
    assert body["updated_at"] is not None


async def test_scanner_endpoint_filters_by_direction(fake_redis) -> None:
    await cache_scan_results(
        fake_redis,
        [
            _entry("BTCUSDT@binance", "long", 70.0, "low"),
            _entry("ETHUSDT@binance", "short", 60.0, "medium"),
        ],
    )

    app.dependency_overrides[get_redis] = lambda: fake_redis
    try:
        client = TestClient(app)
        response = client.get("/scanner", params={"direction": "short"})
    finally:
        app.dependency_overrides.clear()

    body = response.json()
    assert len(body["entries"]) == 1
    assert body["entries"][0]["symbol"] == "ETHUSDT@binance"


async def test_scanner_endpoint_filters_by_risk(fake_redis) -> None:
    await cache_scan_results(
        fake_redis,
        [
            _entry("BTCUSDT@binance", "long", 70.0, "low"),
            _entry("ETHUSDT@binance", "long", 60.0, "high"),
        ],
    )

    app.dependency_overrides[get_redis] = lambda: fake_redis
    try:
        client = TestClient(app)
        response = client.get("/scanner", params={"risk": "high"})
    finally:
        app.dependency_overrides.clear()

    body = response.json()
    assert len(body["entries"]) == 1
    assert body["entries"][0]["symbol"] == "ETHUSDT@binance"


def test_scanner_endpoint_empty_cache_returns_empty_list(fake_redis) -> None:
    app.dependency_overrides[get_redis] = lambda: fake_redis
    try:
        client = TestClient(app)
        response = client.get("/scanner")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"entries": [], "updated_at": None}


def test_scanner_endpoint_rejects_invalid_direction(fake_redis) -> None:
    app.dependency_overrides[get_redis] = lambda: fake_redis
    try:
        client = TestClient(app)
        response = client.get("/scanner", params={"direction": "sideways"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
