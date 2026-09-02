from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.rate_limit import RateLimitMiddleware


class FakeRateLimitRedis:
    def __init__(self) -> None:
        self.counts: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    async def expire(self, key: str, seconds: int) -> None:
        return None


def test_rate_limit_rejects_burst_and_keeps_health_available() -> None:
    test_app = FastAPI()
    test_app.add_middleware(
        RateLimitMiddleware,
        redis=FakeRateLimitRedis(),
        limit=2,
        window_seconds=60,
    )

    @test_app.get("/data")
    async def data() -> dict:
        return {"ok": True}

    @test_app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    client = TestClient(test_app)
    assert client.get("/data").status_code == 200
    assert client.get("/data").status_code == 200
    limited = client.get("/data")
    assert limited.status_code == 429
    assert limited.headers["Retry-After"] == "60"
    assert client.get("/health").status_code == 200
