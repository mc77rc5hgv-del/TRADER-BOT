from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from redis.asyncio import Redis

from app.core.redis import get_redis
from app.scanner.schemas import ScannerEntry
from app.scanner.service import get_cached_scan_results

router = APIRouter(prefix="/scanner", tags=["scanner"])


class ScannerResponse(BaseModel):
    entries: list[ScannerEntry]
    updated_at: str | None


@router.get("", response_model=ScannerResponse)
async def get_scanner_results(
    direction: str | None = Query(default=None, pattern="^(long|short|neutral)$"),
    risk: str | None = Query(default=None, pattern="^(low|medium|high)$"),
    redis: Redis = Depends(get_redis),  # noqa: B008
) -> ScannerResponse:
    entries, updated_at = await get_cached_scan_results(redis)

    if direction:
        entries = [e for e in entries if e.direction == direction]
    if risk:
        entries = [e for e in entries if e.risk_level == risk]

    entries.sort(key=lambda e: e.confidence, reverse=True)

    return ScannerResponse(entries=entries, updated_at=updated_at)
