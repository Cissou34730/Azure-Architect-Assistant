"""Storage / filesystem path settings mixin."""
from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator

# Anchors – this file lives at backend/app/core/settings/storage.py
_BACKEND_ROOT: Path = Path(__file__).resolve().parents[3]
_REPO_ROOT: Path = Path(__file__).resolve().parents[4]


def get_default_env_path() -> Path:
    """Return the repository-level .env path."""
    return _REPO_ROOT / ".env"


def _default_data_root() -> Path:
    """Resolve default data root from env, with safe backend-local fallback.

    Uses os.getenv for DATA_ROOT only — values that live solely in .env are
    not visible here (pydantic-settings loads them later). The fallback is
    backend/data, which is where all runtime databases live.
    """
    data_root_env = os.getenv("DATA_ROOT")
    if data_root_env:
        p = Path(data_root_env)
        return p if p.is_absolute() else (_BACKEND_ROOT / p).resolve()

    return _BACKEND_ROOT / "data"


class StorageSettingsMixin(BaseModel):
    data_root: Path = Field(
        default_factory=_default_data_root,
        description="Canonical root directory for all persisted backend runtime data",
    )
    diagrams_database: Path | None = Field(default=None)
    models_cache_path: Path | None = Field(
        default=None,
        description="Disk cache for OpenAI models list with 7-day TTL",
    )
    project_documents_root: Path | None = Field(
        default=None,
        description="Root directory where uploaded project documents are stored",
    )
    waf_template_cache_dir: Path | None = Field(
        default=None,
        description="Local directory for cached WAF template files",
    )
    projects_database: Path | None = None
    ingestion_database: Path | None = None
    knowledge_bases_root: Path | None = None

    @field_validator("diagrams_database", mode="before")
    @classmethod
    def _normalize_diagrams_db(cls, value: object) -> Path | None:
        if value is None:
            return None
        if isinstance(value, Path):
            return value if value.is_absolute() else (_BACKEND_ROOT / value).resolve()
        if isinstance(value, str):
            v = value.strip()
            if v.startswith("sqlite+aiosqlite:///"):
                path_str = v.replace("sqlite+aiosqlite:///", "", 1)
                p = Path(path_str)
                return p if p.is_absolute() else (_BACKEND_ROOT / p).resolve()
            p = Path(v)
            return p if p.is_absolute() else (_BACKEND_ROOT / p).resolve()
        return value  # type: ignore[return-value]

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
    def _normalize_storage_paths(cls, value: object) -> Path | None:
        if value is None:
            return None
        if isinstance(value, Path):
            return value if value.is_absolute() else (_BACKEND_ROOT / value).resolve()
        if isinstance(value, str):
            v = value.strip()
            if not v:
                return None
            p = Path(v)
            return p if p.is_absolute() else (_BACKEND_ROOT / p).resolve()
        return value  # type: ignore[return-value]

    @model_validator(mode="after")
    def _derive_storage_paths(self) -> "StorageSettingsMixin":
        data_root = self.data_root
        if data_root is None:
            raise ValueError("DATA_ROOT could not be resolved")

        data_root = data_root.resolve()
        data_root.mkdir(parents=True, exist_ok=True)
        self.data_root = data_root

        # Derive paths from data_root when not explicitly configured
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

        storage_paths: dict[str, Path] = {
            "PROJECTS_DATABASE": self.projects_database,         # type: ignore[dict-item]
            "INGESTION_DATABASE": self.ingestion_database,       # type: ignore[dict-item]
            "DIAGRAMS_DATABASE": self.diagrams_database,         # type: ignore[dict-item]
            "MODELS_CACHE_PATH": self.models_cache_path,         # type: ignore[dict-item]
            "KNOWLEDGE_BASES_ROOT": self.knowledge_bases_root,   # type: ignore[dict-item]
            "PROJECT_DOCUMENTS_ROOT": self.project_documents_root,# type: ignore[dict-item]
            "WAF_TEMPLATE_CACHE_DIR": self.waf_template_cache_dir,# type: ignore[dict-item]
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
