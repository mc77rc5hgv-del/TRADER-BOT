from __future__ import annotations

import hashlib
import logging
import time

from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-backed fixed-window limiter, keyed by Telegram auth or client IP.

    Redis failures are fail-open: an infrastructure hiccup must not take the
    API down. Paid AI requests remain protected independently by billing quota.
    """

    def __init__(self, app, redis: Redis, limit: int, window_seconds: int) -> None:
        super().__init__(app)
        self.redis = redis
        self.limit = limit
        self.window_seconds = window_seconds

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path == "/health":
            return await call_next(request)

        identity = request.headers.get("authorization")
        if not identity:
            identity = request.client.host if request.client else "unknown"
        digest = hashlib.sha256(identity.encode()).hexdigest()[:24]
        window = int(time.time()) // self.window_seconds
        key = f"rate_limit:{digest}:{window}"

        try:
            count = await self.redis.incr(key)
            if count == 1:
                await self.redis.expire(key, self.window_seconds + 1)
            if count > self.limit:
                return JSONResponse(
                    {"detail": "Too many requests"},
                    status_code=429,
                    headers={"Retry-After": str(self.window_seconds)},
                )
        except Exception:
            logger.warning("Rate-limit backend unavailable; allowing request", exc_info=True)

        return await call_next(request)
