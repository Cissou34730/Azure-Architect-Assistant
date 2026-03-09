"""Storage / filesystem path settings mixin."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Final

from pydantic import BaseModel, Field, field_validator, model_validator

# Anchors - this file lives at backend/app/core/settings/storage.py
_BACKEND_ROOT: Path = Path(__file__).resolve().parents[3]
_REPO_ROOT: Path = Path(__file__).resolve().parents[4]
_DATABASE_OR_FILE_SUFFIXES: Final[tuple[str, ...]] = ("_database", "_path")
_DERIVED_STORAGE_PATHS: Final[dict[str, str]] = {
    "projects_database": "projects.db",
    "ingestion_database": "ingestion.db",
    "diagrams_database": "diagrams.db",
    "models_cache_path": "openai_models_cache.json",
    "knowledge_bases_root": "knowledge_bases",
    "project_documents_root": "project_documents",
    "waf_template_cache_dir": "waf_template_cache",
}


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


def _resolve_backend_path(path: Path) -> Path:
    """Resolve relative paths against the backend root."""
    return path if path.is_absolute() else (_BACKEND_ROOT / path).resolve()


def _normalize_optional_path(value: object) -> Path | None | object:
    """Normalize string and Path values while letting Pydantic reject other types."""
    if value is None:
        return None
    if isinstance(value, Path):
        return _resolve_backend_path(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        return _resolve_backend_path(Path(stripped))
    return value


def _ensure_within_data_root(*, field_name: str, path: Path, data_root: Path) -> Path:
    """Resolve, validate, and create a storage path constrained to DATA_ROOT."""
    resolved = path.resolve()
    try:
        resolved.relative_to(data_root)
    except ValueError as exc:
        env_name = field_name.upper()
        raise ValueError(
            f"{env_name} must be under DATA_ROOT ({data_root}), got {resolved}"
        ) from exc

    if field_name.endswith(_DATABASE_OR_FILE_SUFFIXES):
        resolved.parent.mkdir(parents=True, exist_ok=True)
    else:
        resolved.mkdir(parents=True, exist_ok=True)
    return resolved


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
            return _resolve_backend_path(value)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("sqlite+aiosqlite:///"):
                stripped = stripped.replace("sqlite+aiosqlite:///", "", 1)
            return _resolve_backend_path(Path(stripped))
        return None

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
        normalized = _normalize_optional_path(value)
        return normalized if isinstance(normalized, Path) or normalized is None else None

    def _apply_default_storage_paths(self, *, data_root: Path) -> None:
        for field_name, relative_path in _DERIVED_STORAGE_PATHS.items():
            if getattr(self, field_name) is None:
                setattr(self, field_name, data_root / relative_path)

    def _resolve_storage_paths(self, *, data_root: Path) -> None:
        for field_name in _DERIVED_STORAGE_PATHS:
            path = getattr(self, field_name)
            if path is None:
                raise ValueError(f"{field_name.upper()} could not be resolved")
            setattr(
                self,
                field_name,
                _ensure_within_data_root(
                    field_name=field_name,
                    path=path,
                    data_root=data_root,
                ),
            )

    @model_validator(mode="after")
    def _derive_storage_paths(self) -> StorageSettingsMixin:
        data_root = self.data_root
        if data_root is None:
            raise ValueError("DATA_ROOT could not be resolved")

        data_root = data_root.resolve()
        data_root.mkdir(parents=True, exist_ok=True)
        self.data_root = data_root

        self._apply_default_storage_paths(data_root=data_root)
        self._resolve_storage_paths(data_root=data_root)

        return self
