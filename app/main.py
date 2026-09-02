from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.market.router import router as market_router
from app.webapp.router import router as webapp_router

settings = get_settings()

app = FastAPI(title="TRADE AI API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(market_router)
app.include_router(webapp_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "env": settings.env}
