"""
Application configuration helpers.
Centralized settings loader with .env support.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

from config import (
    get_settings as get_ingestion_settings,
    get_kb_defaults,
    get_openai_settings,
    get_kb_storage_root,
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

    # Agent system settings
    mcp_config_path: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parents[2] / "config" / "mcp" / "mcp_config.json",
        env="MCP_CONFIG_PATH"
    )
    mcp_default_timeout: int = Field(30, env="MCP_DEFAULT_TIMEOUT")
    mcp_max_retries: int = Field(3, env="MCP_MAX_RETRIES")

    @validator("cors_allow_origins", pre=True)
    def _split_origins(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @validator("mcp_config_path", pre=True)
    def _resolve_mcp_path(cls, value):
        if isinstance(value, str):
            return Path(value)
        return value

    class Config:
        env_file = str(_default_env_path())
        env_file_encoding = "utf-8"
        case_sensitive = False

    def load_mcp_config(self) -> Dict[str, Any]:
        """
        Load MCP configuration from file.

        Returns:
            Dictionary with MCP server configurations

        Raises:
            FileNotFoundError: If config file doesn't exist
            json.JSONDecodeError: If config file is invalid JSON
        """
        if not self.mcp_config_path.exists():
            raise FileNotFoundError(
                f"MCP config file not found: {self.mcp_config_path}. "
                f"Create it or set MCP_CONFIG_PATH environment variable."
            )

        with open(self.mcp_config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_mcp_server_config(self, server_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific MCP server.

        Args:
            server_name: Name of the MCP server (e.g., "microsoft_learn")

        Returns:
            Server configuration dictionary

        Raises:
            KeyError: If server not found in config
        """
        config = self.load_mcp_config()

        if server_name not in config:
            raise KeyError(
                f"MCP server '{server_name}' not found in config. "
                f"Available servers: {list(config.keys())}"
            )

        return config[server_name]


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
    "get_kb_storage_root",
    "KBDefaults",
    "OpenAISettings",
    "IngestionSettings",
]
