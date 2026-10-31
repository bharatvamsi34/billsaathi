"""Application settings, loaded from the environment and api/.env.

Secrets are SecretStr so they never appear in logs, reprs or tracebacks.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

API_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=API_DIR / ".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,  # blank lines copied from .env.example fall back to defaults
        extra="ignore",
    )

    # Meta Model API — values come from dev.meta.ai "Get code"; no guessed defaults.
    meta_api_key: SecretStr | None = None
    meta_api_base_url: str | None = None
    meta_model_spark: str | None = None
    meta_model_wonder: str | None = None
    meta_model_sam: str | None = None
    meta_model_transcribe: str | None = None

    # Baseten (OpenAI-compatible) — open-weight Muse Spark Open for Privacy Mode.
    baseten_api_key: SecretStr | None = None
    baseten_base_url: str = "https://inference.baseten.co/v1"
    baseten_model: str = "meta-models/muse-spark-open-1026"

    app_env: Literal["local", "ci", "prod"] = "local"
    log_level: str = "INFO"

    # Checks API
    cors_origins: str = "http://localhost:3000"  # comma-separated; our web app's origin(s)
    rate_limit_per_minute: int = 10  # new checks per client IP
    daily_spend_cap_usd: float = 5.0  # model spend per UTC day; above it new checks get 503
    check_ttl_seconds: int = 600  # finished or paused checks are kept in memory this long
    model_timeout_seconds: float = 30.0

    # WhatsApp Cloud API webhook (Meta test number). Without the App Secret and verify token
    # the webhook refuses everything.
    whatsapp_access_token: SecretStr | None = None
    whatsapp_phone_number_id: str | None = None
    whatsapp_app_secret: SecretStr | None = None  # X-Hub-Signature-256 key; also salts sender ids
    whatsapp_verify_token: SecretStr | None = None
    whatsapp_graph_base_url: str = "https://graph.facebook.com"
    whatsapp_graph_version: str = "v25.0"
    whatsapp_rate_limit_per_minute: int = 5  # new checks per sender
    whatsapp_question_ttl_seconds: int = 600  # unanswered question -> CAUTION
    web_app_url: str = "https://zealous-coast-09279dd00.1.azurestaticapps.net"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
