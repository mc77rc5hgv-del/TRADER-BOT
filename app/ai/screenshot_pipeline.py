"""Screenshot analysis pipeline (TZ sections 2.1, 13 step 6) — the vision
half of the Intent Router. A screenshot is only ever used to identify the
symbol/timeframe; once resolved, the rest of the pipeline is identical to
the text scenario (app.ai.pipeline) and never reads market numbers off the
image itself."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.image_utils import InvalidImageError, strip_image_metadata
from app.ai.models import PredictionSource, Screenshot
from app.ai.pipeline import run_chat_analysis
from app.ai.provider import LLMProvider
from app.ai.schemas import AnalysisResult
from app.ai.screenshot_storage import ScreenshotStorage
from app.ai.timeframe import DEFAULT_TF, normalize_tf_guess
from app.ai.usage import record_ai_request
from app.config import get_settings
from app.market.service import MarketDataEngine
from app.market.symbols import normalize_symbol, suggest_symbols


@dataclass
class ScreenshotAnalysisOutcome:
    status: str  # "resolved" | "ambiguous" | "unresolved" | "invalid_image"
    result: AnalysisResult | None = None
    suggestions: list[str] = field(default_factory=list)


async def run_screenshot_analysis(
    image_bytes: bytes,
    market_engine: MarketDataEngine,
    llm_provider: LLMProvider,
    storage: ScreenshotStorage,
    db_session: AsyncSession,
    user_id: int,
) -> ScreenshotAnalysisOutcome:
    settings = get_settings()

    try:
        clean_bytes, media_type = await asyncio.to_thread(strip_image_metadata, image_bytes)
    except InvalidImageError:
        return ScreenshotAnalysisOutcome(status="invalid_image")

    storage_key = f"{user_id}/{uuid.uuid4().hex}.jpg"
    await storage.save(storage_key, clean_bytes)

    uploaded_at = datetime.now(UTC)
    db_session.add(
        Screenshot(
            user_id=user_id,
            storage_key=storage_key,
            expires_at=uploaded_at + timedelta(days=settings.screenshot_retention_days),
        )
    )
    await db_session.commit()

    started_at = datetime.now(UTC)
    extraction, usage = await llm_provider.extract_chart_info(clean_bytes, media_type)
    latency_ms = int((datetime.now(UTC) - started_at).total_seconds() * 1000)
    await record_ai_request(db_session, user_id, "vision_extraction", usage, latency_ms)

    tf = normalize_tf_guess(extraction.timeframe_guess) or DEFAULT_TF

    canonical = normalize_symbol(extraction.symbol_guess) if extraction.symbol_guess else None
    if canonical is None:
        suggestions = suggest_symbols(extraction.symbol_guess)
        status = "ambiguous" if suggestions else "unresolved"
        return ScreenshotAnalysisOutcome(status=status, suggestions=suggestions)

    # Re-normalized from the same raw guess inside run_chat_analysis via
    # market_engine.get_market_state() - passing the raw guess (not the
    # already-canonical form) keeps normalize_symbol's contract simple.
    result = await run_chat_analysis(
        extraction.symbol_guess,
        tf,
        market_engine,
        llm_provider,
        db_session,
        user_id,
        source=PredictionSource.SCREENSHOT,
    )
    return ScreenshotAnalysisOutcome(status="resolved", result=result)
