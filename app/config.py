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

    # Comma-separated CORS origins the API accepts requests from (the Mini
    # App's dev server by default; mini_app_url is added automatically).
    cors_allow_origins: str = "http://localhost:3000"

    # Shared market-state cache TTL, seconds (TZ section 5.3: 30-90s window)
    market_cache_ttl_seconds: int = 60

    # Coarse API abuse protection. Billing quotas remain the authoritative
    # per-user limit for paid AI work; this protects all HTTP endpoints from
    # bursts before they reach application code.
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60

    # Screenshot handling (TZ sections 6.4, 10). Local filesystem storage is
    # a dev/MVP fallback behind the ScreenshotStorage interface - swap in an
    # S3-compatible implementation for production without touching callers.
    screenshot_storage_dir: str = "./data/screenshots"
    screenshot_retention_days: int = 30
    screenshot_max_bytes: int = 8 * 1024 * 1024

    @property
    def cors_allow_origins_list(self) -> list[str]:
        origins = [
            origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()
        ]
        if self.mini_app_url and self.mini_app_url not in origins:
            origins.append(self.mini_app_url)
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()
