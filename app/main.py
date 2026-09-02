from fastapi import FastAPI

from app.config import get_settings
from app.market.router import router as market_router

settings = get_settings()

app = FastAPI(title="TRADE AI API", version="0.1.0")
app.include_router(market_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "env": settings.env}
