from functools import lru_cache
from typing import Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    supabase_url: str
    supabase_anon_key: str
    cors_origins: str
    # Optional: the API server boots fine without it. Only required when
    # actually running an offline ingestion script (app/ingestion/), which
    # will raise a clear error itself if this is missing at that point.
    supabase_service_role_key: Optional[str] = None

    # Optional: AI provider configuration (Anthropic Claude). The API
    # server boots fine without it. Only required when actually
    # constructing an AI provider (app/ai/), which raises a clear error
    # itself if the key is missing at that point — same pattern as
    # supabase_service_role_key above.
    anthropic_api_key: Optional[str] = None
    ai_model: str = "claude-opus-5"
    ai_timeout_seconds: float = 30.0
    ai_max_retries: int = 2
    # "fake" (default): use DevAIProvider — deterministic mock data, no
    # API key needed, no external calls. Local development works out of
    # the box, including when ANTHROPIC_API_KEY is unset or the account
    # has no credits. Set to "claude" (and set ANTHROPIC_API_KEY) to use
    # the real Anthropic provider. See app/ai/factory.get_ai_provider().
    ai_provider: Literal["fake", "claude"] = "fake"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
