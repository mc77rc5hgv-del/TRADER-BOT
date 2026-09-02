from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

# Internal timeframe vocabulary (TZ section 3.2: 5m/15m/1H/4H/1D switcher).
# Values match Binance kline interval strings 1:1 so no translation table
# is needed for the one exchange MVP supports.
ALLOWED_TIMEFRAMES = ("1m", "5m", "15m", "1h", "4h", "1d")


class Candle(BaseModel):
    open_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    close_time: datetime


class Ticker(BaseModel):
    symbol: str
    price: float
    price_change_percent_24h: float


class MarketState(BaseModel):
    """Cacheable snapshot handed to the Technical Analysis / Probability /
    Risk engines and, compressed, to the AI Reasoning Layer (TZ section 5.3)."""

    symbol: str
    tf: str
    ticker: Ticker
    candles: list[Candle]
    fetched_at: datetime
