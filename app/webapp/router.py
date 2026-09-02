from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.repository import get_or_create_user
from app.config import get_settings
from app.db.session import get_session
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


@router.post("/auth")
async def webapp_auth(
    data: dict = Depends(get_validated_init_data),  # noqa: B008
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict:
    user_payload = data.get("user") or {}
    telegram_id = user_payload.get("id")
    if telegram_id is None:
        raise HTTPException(status_code=400, detail="initData has no user")

    user = await get_or_create_user(session, telegram_id, user_payload.get("username"))

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
