from __future__ import annotations

from datetime import UTC, datetime

import httpx

from app.market.schemas import Candle, Ticker

BASE_URL = "https://api.binance.com"


class BinanceClient:
    """Thin wrapper around Binance's public market-data REST endpoints.

    These are public endpoints — no API key required (TZ sections 5.1, 53).
    A single instance is shared across all requests; callers must not open
    one connection per user."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(base_url=BASE_URL, timeout=10.0)
        self._owns_client = client is None

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def get_klines(self, symbol: str, interval: str, limit: int = 200) -> list[Candle]:
        response = await self._client.get(
            "/api/v3/klines",
            params={"symbol": symbol, "interval": interval, "limit": limit},
        )
        response.raise_for_status()
        rows = response.json()
        return [
            Candle(
                open_time=datetime.fromtimestamp(row[0] / 1000, tz=UTC),
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5]),
                close_time=datetime.fromtimestamp(row[6] / 1000, tz=UTC),
            )
            for row in rows
        ]

    async def get_ticker_24hr(self, symbol: str) -> Ticker:
        response = await self._client.get("/api/v3/ticker/24hr", params={"symbol": symbol})
        response.raise_for_status()
        data = response.json()
        return Ticker(
            symbol=symbol,
            price=float(data["lastPrice"]),
            price_change_percent_24h=float(data["priceChangePercent"]),
        )
