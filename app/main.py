from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core.rate_limit import RateLimitMiddleware
from app.core.redis import get_redis
from app.market.router import router as market_router
from app.scanner.router import router as scanner_router
from app.webapp.router import router as webapp_router

settings = get_settings()

app = FastAPI(title="TRADE AI API", version="0.1.0")

app.add_middleware(
    RateLimitMiddleware,
    redis=get_redis(),
    limit=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window_seconds,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(market_router)
app.include_router(scanner_router)
app.include_router(webapp_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "env": settings.env}
