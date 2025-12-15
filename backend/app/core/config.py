"""
Application configuration helpers.
Centralized settings loader with .env support.
"""

from functools import lru_cache
from pathlib import Path
from typing import List

from config import (
    get_settings as get_ingestion_settings,
    get_kb_defaults,
    get_openai_settings,
    KBDefaults,
    OpenAISettings,
    IngestionSettings,
)

from dotenv import load_dotenv
from pydantic import Field, validator
from pydantic_settings import BaseSettings


def _default_env_path() -> Path:
    """Return the repository-level .env path (one level above backend)."""
    return Path(__file__).resolve().parents[2] / ".env"


class AppSettings(BaseSettings):
    """Top-level application settings."""

    env: str = Field("development", env="ENV")
    backend_port: int = Field(8000, env="BACKEND_PORT")
    cors_allow_origins: List[str] = Field(default_factory=lambda: ["*"], env="CORS_ALLOW_ORIGINS")
    log_level: str = Field("INFO", env="LOG_LEVEL")

    @validator("cors_allow_origins", pre=True)
    def _split_origins(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    class Config:
        env_file = str(_default_env_path())
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_app_settings() -> AppSettings:
    """Return cached application settings (loads .env once)."""
    load_dotenv(dotenv_path=_default_env_path())
    return AppSettings()


def get_backend_root() -> Path:
    """Backend root directory path."""
    return Path(__file__).resolve().parents[2]


# Convenience re-exports for legacy ingestion settings
__all__ = [
    "AppSettings",
    "get_app_settings",
    "get_backend_root",
    "get_ingestion_settings",
    "get_kb_defaults",
    "get_openai_settings",
    "KBDefaults",
    "OpenAISettings",
    "IngestionSettings",
]
