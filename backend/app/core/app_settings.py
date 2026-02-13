"""
Application configuration helpers.
Centralized settings loader with .env support.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from config import (
    IngestionSettings,
    KBDefaults,
    OpenAISettings,
    get_kb_defaults,
    get_kb_storage_root,
    get_openai_settings,
)
from config import (
    get_settings as get_ingestion_settings,
)


def _default_env_path() -> Path:
    """Return the repository-level .env path (one level above backend)."""
    return Path(__file__).resolve().parents[3] / ".env"


class AppSettings(BaseSettings):
    """Top-level application settings."""

    # Strict settings config with explicit env file and no extras.
    model_config = SettingsConfigDict(
        env_file=str(_default_env_path()),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="forbid",
    )

    env: str = Field("development")
    app_version: str = "4.0.0"
    backend_host: str = Field("0.0.0.0")
    backend_port: int = Field(8000, ge=1, le=65535)
    cors_allow_origins: list[str] = Field(default_factory=lambda: ["*"])
    log_level: str = Field("INFO")

    # Agent system settings
    mcp_config_path: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parents[2]
        / "config"
        / "mcp"
        / "mcp_config.json",
    )
    mcp_default_timeout: int = Field(30)
    mcp_max_retries: int = Field(3)

    # LangGraph migration feature flags (Phase 3+)
    aaa_use_langgraph: bool = Field(default=True)
    # Preferred selection knob: explicit engine choice.
    # Backward compatible with AAA_USE_LANGGRAPH.
    aaa_agent_engine: Literal["langchain", "langgraph"] = Field(default="langgraph")
    aaa_enable_stage_routing: bool = Field(default=False)  # Phase 5
    aaa_enable_multi_agent: bool = Field(default=False)  # Phase 6

    @field_validator("aaa_agent_engine", mode="before")
    @classmethod
    def _normalize_agent_engine(cls, value):
        if value is None:
            return "langgraph"
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @model_validator(mode="after")
    def _apply_langgraph_compat_flags(self):
        # If the old boolean is set, prefer LangGraph unless the engine was
        # explicitly configured to something else.
        if self.aaa_use_langgraph and self.aaa_agent_engine == "langchain":
            self.aaa_agent_engine = "langgraph"

        # Keep bool in sync for existing call sites.
        if self.aaa_agent_engine == "langgraph":
            self.aaa_use_langgraph = True

        return self

    # Diagram generation settings
    diagrams_database: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parents[2]
        / "data"
        / "diagrams.db",
    )

    # WAF Checklist Normalization Settings
    aaa_feature_waf_normalized: bool = Field(
        default=False,
        description="Enable normalized WAF checklist storage (dual-write mode)"
    )

    waf_namespace_uuid: str = Field(
        default="3a7e8c2f-1b4d-4f5e-9c3d-2a8b7e6f1c4d",
        description="Namespace UUID for deterministic checklist item IDs (UUID v5)"
    )

    waf_template_cache_dir: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parents[2]
        / "config"
        / "checklists",
        description="Local directory for cached WAF template files"
    )

    waf_backfill_batch_size: int = Field(
        default=50,
        description="Number of projects to process per backfill batch"
    )

    waf_sync_chunk_size: int = Field(
        default=500,
        description="Number of items to process per database transaction during sync"
    )

    plantuml_jar_path: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parents[2]
        / "lib"
        / "plantuml.jar",
    )
    diagram_openai_model: str = Field("gpt-4-turbo-preview")
    diagram_max_retries: int = Field(3)
    diagram_generation_timeout: int = Field(30)

    # Explicitly model commonly-present env keys to avoid extras in .env
    frontend_port: int | None = None
    backend_url: str | None = None
    openai_api_key: str | None = None
    openai_model: str | None = None
    openai_embedding_model: str | None = None
    projects_database: Path | None = None
    ingestion_database: Path | None = None
    knowledge_bases_root: Path | None = None
    vite_banner_message: str | None = None

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def _split_origins(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("mcp_config_path", mode="before")
    @classmethod
    def _resolve_mcp_path(cls, value):
        if isinstance(value, str):
            return Path(value)
        return value

    @field_validator("diagrams_database", mode="before")
    @classmethod
    def _normalize_diagrams_db(cls, value):
        repo_root = Path(__file__).resolve().parents[3]
        if isinstance(value, Path):
            return value if value.is_absolute() else (repo_root / value).resolve()
        if isinstance(value, str):
            v = value.strip()
            if v.startswith("sqlite+aiosqlite:///"):
                # Strip DSN prefix and normalize path
                path_str = v.replace("sqlite+aiosqlite:///", "", 1)
                p = Path(path_str)
                return p if p.is_absolute() else (repo_root / p).resolve()
            # Treat as filesystem path
            p = Path(v)
            return p if p.is_absolute() else (repo_root / p).resolve()
        return value

    # Pydantic v2 config is defined via model_config above.

    def load_mcp_config(self) -> dict[str, Any]:
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

        with open(self.mcp_config_path, encoding="utf-8") as f:
            return json.load(f)

    def get_mcp_server_config(self, server_name: str) -> dict[str, Any]:
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


@lru_cache
def get_app_settings() -> AppSettings:
    """Return cached application settings (loads .env once)."""
    load_dotenv(dotenv_path=_default_env_path())
    return AppSettings()


def get_settings() -> AppSettings:
    """Backward-compatible alias for settings access.

    Some routers/services import `get_settings` from this module.
    Prefer using `get_app_settings` (or `app.core.container.get_settings`) going forward.
    """
    return get_app_settings()


def get_backend_root() -> Path:
    """Backend root directory path."""
    return Path(__file__).resolve().parents[2]


# Convenience re-exports for legacy ingestion settings
__all__ = [
    "AppSettings",
    "IngestionSettings",
    "KBDefaults",
    "OpenAISettings",
    "get_app_settings",
    "get_backend_root",
    "get_ingestion_settings",
    "get_kb_defaults",
    "get_kb_storage_root",
    "get_openai_settings",
    "get_settings",
]

