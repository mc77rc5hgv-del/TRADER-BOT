from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.dependencies import get_llm_provider
from app.ai.pipeline import SymbolNotRecognizedError, run_chat_analysis
from app.ai.provider import LLMProvider
from app.ai.schemas import AnalysisResult
from app.bot.repository import get_or_create_user
from app.config import get_settings
from app.db.session import get_session
from app.market.router import get_market_data_engine
from app.market.service import MarketDataEngine
from app.users.models import User
from app.webapp.auth import InvalidInitDataError, validate_init_data

router = APIRouter(prefix="/webapp", tags=["webapp"])


def _extract_init_data(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("tma "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")
    return authorization.removeprefix("tma ").strip()


async def get_validated_init_data(authorization: str | None = Header(default=None)) -> dict:
    """Reusable dependency for any webapp endpoint that needs to know who's
    calling — validates the `Authorization: tma <initData>` header and
    returns the parsed fields. Every future webapp router should depend on
    this rather than re-validating initData itself."""
    settings = get_settings()
    init_data = _extract_init_data(authorization)
    try:
        return validate_init_data(init_data, settings.telegram_bot_token)
    except InvalidInitDataError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


async def get_current_user(
    data: dict = Depends(get_validated_init_data),  # noqa: B008
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> User:
    """Upserts and returns the calling user — the shared second half of
    get_validated_init_data that every authenticated webapp endpoint needs."""
    user_payload = data.get("user") or {}
    telegram_id = user_payload.get("id")
    if telegram_id is None:
        raise HTTPException(status_code=400, detail="initData has no user")
    return await get_or_create_user(session, telegram_id, user_payload.get("username"))


@router.post("/auth")
async def webapp_auth(user: User = Depends(get_current_user)) -> dict:  # noqa: B008
    return {
        "ok": True,
        "user": {
            "id": user.id,
            "telegram_id": user.telegram_id,
            "username": user.username,
            "trading_style": user.trading_style.value if user.trading_style else None,
            "risk_profile": user.risk_profile.value if user.risk_profile else None,
        },
    }


class AnalyzeRequest(BaseModel):
    symbol: str
    tf: str = "1h"


@router.post("/analyze", response_model=AnalysisResult)
async def webapp_analyze(
    payload: AnalyzeRequest,
    user: User = Depends(get_current_user),  # noqa: B008
    session: AsyncSession = Depends(get_session),  # noqa: B008
    market_engine: MarketDataEngine = Depends(get_market_data_engine),  # noqa: B008
    llm_provider: LLMProvider = Depends(get_llm_provider),  # noqa: B008
) -> AnalysisResult:
    """Same pipeline as the bot's /analyze command (app/ai/pipeline.py) —
    the Mini App's AI tab is another front door onto it, not a separate
    implementation (TZ section 8: "тот же ответ, что в боте")."""
    try:
        return await run_chat_analysis(payload.symbol, payload.tf, market_engine, llm_provider, session, user.id)
    except SymbolNotRecognizedError as exc:
        raise HTTPException(status_code=404, detail=f"Symbol not recognized: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
