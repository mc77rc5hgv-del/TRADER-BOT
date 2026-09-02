from functools import lru_cache
from pathlib import Path

import anthropic

from app.ai.provider import AnthropicProvider, LLMProvider
from app.ai.screenshot_storage import LocalFilesystemStorage, ScreenshotStorage
from app.config import get_settings


@lru_cache
def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    # An explicit LLM_API_KEY overrides the SDK's own credential resolution
    # (ANTHROPIC_API_KEY / ant auth profile); leave client unset to use that
    # default resolution when no override is configured.
    default_headers = None
    if settings.anthropic_workspace_id:
        default_headers = {"anthropic-workspace-id": settings.anthropic_workspace_id}

    client = None
    if settings.llm_api_key or default_headers:
        client = anthropic.AsyncAnthropic(
            api_key=settings.llm_api_key or None,
            default_headers=default_headers,
        )
    return AnthropicProvider(model=settings.llm_model, client=client)


@lru_cache
def get_screenshot_storage() -> ScreenshotStorage:
    settings = get_settings()
    return LocalFilesystemStorage(Path(settings.screenshot_storage_dir))
