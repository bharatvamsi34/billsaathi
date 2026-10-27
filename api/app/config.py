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


@lru_cache
def get_settings() -> Settings:
    return Settings()
