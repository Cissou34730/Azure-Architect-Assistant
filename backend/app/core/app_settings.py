"""
Application configuration helpers.
Centralized settings loader with .env support.
"""

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

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


def _default_data_root() -> Path:
    """Resolve default persistent data root from env, with safe repo-local fallback."""
    repo_root = Path(__file__).resolve().parents[3]

    data_root_env = os.getenv("DATA_ROOT")
    if data_root_env:
        p = Path(data_root_env)
        if not p.is_absolute():
            p = (repo_root / p).resolve()
        return p

    projects_db_env = os.getenv("PROJECTS_DATABASE")
    if projects_db_env:
        p = Path(projects_db_env)
        if not p.is_absolute():
            p = (repo_root / p).resolve()
        return p.parent

    knowledge_bases_root_env = os.getenv("KNOWLEDGE_BASES_ROOT")
    if knowledge_bases_root_env:
        p = Path(knowledge_bases_root_env)
        if not p.is_absolute():
            p = (repo_root / p).resolve()
        return p.parent

    return Path(__file__).resolve().parents[2] / "data"


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

    # LangGraph runtime flags
    aaa_use_langgraph: bool = Field(default=True)
    aaa_enable_stage_routing: bool = Field(default=False)  # Phase 5
    aaa_enable_multi_agent: bool = Field(default=False)  # Phase 6

    @model_validator(mode="after")
    def _apply_langgraph_compat_flags(self):
        # Backend runtime is LangGraph-only.
        self.aaa_use_langgraph = True

        return self

    # Diagram generation settings
    data_root: Path = Field(
        default_factory=_default_data_root,
        description="Canonical root directory for all persisted backend runtime data",
    )

    diagrams_database: Path | None = Field(default=None)
    
    # Models cache settings
    models_cache_path: Path | None = Field(
        default=None,
        description="Disk cache for OpenAI models list with 7-day TTL"
    )

    project_documents_root: Path | None = Field(
        default=None,
        description="Root directory where uploaded project documents are stored"
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

    waf_template_cache_dir: Path | None = Field(
        default=None,
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
    diagram_max_retries: int = Field(3)
    diagram_generation_timeout: int = Field(30)

    # LLM extraction and JSON repair settings
    llm_analyze_max_tokens: int = Field(
        default=12000,
        ge=512,
        le=32768,
        description="Max completion tokens used for document analysis extraction",
    )
    llm_json_repair_min_tokens: int = Field(
        default=1500,
        ge=256,
        le=16384,
        description="Minimum token budget for JSON repair retries",
    )
    llm_json_repair_token_divisor: int = Field(
        default=2,
        ge=1,
        le=16,
        description="Repair token budget divisor based on original request budget",
    )
    llm_response_preview_log_chars: int = Field(
        default=500,
        ge=100,
        le=10000,
        description="Max chars for debug response previews",
    )
    llm_response_error_log_chars: int = Field(
        default=1000,
        ge=100,
        le=20000,
        description="Max chars for error response snippets",
    )
    llm_request_timeout_seconds: float = Field(
        default=600.0,
        ge=10.0,
        le=3600.0,
        description="Timeout in seconds for LLM requests (SDK default is 10 minutes)",
    )

    # Explicitly model commonly-present env keys to avoid extras in .env
    frontend_port: int | None = None
    backend_url: str | None = None
    openai_api_key: str | None = None
    openai_model: str | None = None
    openai_embedding_model: str | None = None
    ai_llm_provider: str | None = None
    ai_embedding_provider: str | None = None
    ai_fallback_enabled: bool | None = None
    ai_fallback_provider: str | None = None
    ai_fallback_on_transient_only: bool | None = None
    ai_openai_api_key: str | None = None
    ai_openai_llm_model: str | None = None
    ai_openai_embedding_model: str | None = None
    ai_azure_openai_endpoint: str | None = None
    ai_azure_openai_api_key: str | None = None
    ai_azure_openai_api_version: str | None = None
    ai_azure_llm_deployment: str | None = None
    ai_azure_embedding_deployment: str | None = None
    ai_azure_llm_deployments: str | None = None
    projects_database: Path | None = None
    ingestion_database: Path | None = None
    knowledge_bases_root: Path | None = None
    vite_banner_message: str | None = None
    vite_api_base: str | None = None

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
        if value is None:
            return None
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

    @field_validator(
        "data_root",
        "models_cache_path",
        "project_documents_root",
        "waf_template_cache_dir",
        "projects_database",
        "ingestion_database",
        "knowledge_bases_root",
        mode="before",
    )
    @classmethod
    def _normalize_storage_paths(cls, value):
        repo_root = Path(__file__).resolve().parents[3]
        if value is None:
            return None
        if isinstance(value, Path):
            return value if value.is_absolute() else (repo_root / value).resolve()
        if isinstance(value, str):
            v = value.strip()
            if not v:
                return None
            p = Path(v)
            return p if p.is_absolute() else (repo_root / p).resolve()
        return value

    @model_validator(mode="after")
    def _derive_and_validate_storage_paths(self):
        data_root = self.data_root
        if data_root is None:
            raise ValueError("DATA_ROOT could not be resolved")

        data_root = data_root.resolve()
        data_root.mkdir(parents=True, exist_ok=True)
        self.data_root = data_root

        if self.projects_database is None:
            self.projects_database = data_root / "projects.db"
        if self.ingestion_database is None:
            self.ingestion_database = data_root / "ingestion.db"
        if self.diagrams_database is None:
            self.diagrams_database = data_root / "diagrams.db"
        if self.models_cache_path is None:
            self.models_cache_path = data_root / "openai_models_cache.json"
        if self.knowledge_bases_root is None:
            self.knowledge_bases_root = data_root / "knowledge_bases"
        if self.project_documents_root is None:
            self.project_documents_root = data_root / "project_documents"
        if self.waf_template_cache_dir is None:
            self.waf_template_cache_dir = data_root / "waf_template_cache"

        storage_paths = {
            "PROJECTS_DATABASE": self.projects_database,
            "INGESTION_DATABASE": self.ingestion_database,
            "DIAGRAMS_DATABASE": self.diagrams_database,
            "MODELS_CACHE_PATH": self.models_cache_path,
            "KNOWLEDGE_BASES_ROOT": self.knowledge_bases_root,
            "PROJECT_DOCUMENTS_ROOT": self.project_documents_root,
            "WAF_TEMPLATE_CACHE_DIR": self.waf_template_cache_dir,
        }

        for name, path in storage_paths.items():
            resolved = path.resolve()
            try:
                resolved.relative_to(data_root)
            except ValueError as exc:
                raise ValueError(
                    f"{name} must be under DATA_ROOT ({data_root}), got {resolved}"
                ) from exc
            if name.endswith("_DATABASE") or name.endswith("_PATH"):
                resolved.parent.mkdir(parents=True, exist_ok=True)
            else:
                resolved.mkdir(parents=True, exist_ok=True)
            setattr(self, name.lower(), resolved)

        return self

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

