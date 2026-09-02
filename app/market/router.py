from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException

from app.config import get_settings
from app.core.redis import get_redis
from app.market.binance_client import BinanceClient
from app.market.schemas import MarketState
from app.market.service import MarketDataEngine, UnsupportedExchangeError

router = APIRouter(prefix="/market", tags=["market"])


@lru_cache
def _get_binance_client() -> BinanceClient:
    return BinanceClient()


def get_market_data_engine() -> MarketDataEngine:
    settings = get_settings()
    return MarketDataEngine(_get_binance_client(), get_redis(), settings.market_cache_ttl_seconds)


@router.get("/{symbol}/state", response_model=MarketState)
async def get_market_state(
    symbol: str,
    tf: str = "1h",
    engine: MarketDataEngine = Depends(get_market_data_engine),  # noqa: B008
) -> MarketState:
    try:
        state = await engine.get_market_state(symbol, tf)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except UnsupportedExchangeError as exc:
        raise HTTPException(status_code=501, detail=f"Exchange not supported: {exc}") from exc

    if state is None:
        raise HTTPException(status_code=404, detail=f"Symbol not recognized: {symbol}")
    return state
