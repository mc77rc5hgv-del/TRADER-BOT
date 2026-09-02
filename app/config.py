from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: str = "dev"

    telegram_bot_token: str = ""

    database_url: str = "postgresql+asyncpg://trade_ai:trade_ai@localhost:5432/trade_ai"

    redis_url: str = "redis://localhost:6379/0"

    llm_api_key: str = ""
    llm_model: str = "claude-opus-5"

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # https URL of the deployed Mini App (empty until Phase 1 step 7 ships it)
    mini_app_url: str = ""

    # Shared market-state cache TTL, seconds (TZ section 5.3: 30-90s window)
    market_cache_ttl_seconds: int = 60

    # Screenshot handling (TZ sections 6.4, 10). Local filesystem storage is
    # a dev/MVP fallback behind the ScreenshotStorage interface - swap in an
    # S3-compatible implementation for production without touching callers.
    screenshot_storage_dir: str = "./data/screenshots"
    screenshot_retention_days: int = 30
    screenshot_max_bytes: int = 8 * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
