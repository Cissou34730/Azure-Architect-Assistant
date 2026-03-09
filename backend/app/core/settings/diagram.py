"""Diagram generation settings mixin."""
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field, field_validator

# Anchors - this file lives at backend/app/core/settings/diagram.py
_BACKEND_ROOT: Path = Path(__file__).resolve().parents[3]


class DiagramSettingsMixin(BaseModel):
    plantuml_jar_path: Path = Field(
        default_factory=lambda: _BACKEND_ROOT / "lib" / "plantuml.jar",
    )
    diagram_max_retries: int = Field(default=3)
    diagram_generation_timeout: int = Field(default=30)
    diagram_temperature: float = Field(
        default=0.3,
        description="LLM temperature used when generating Mermaid diagrams",
    )
    diagram_max_nodes: int = Field(
        default=20,
        description="Maximum number of nodes rendered in a single Mermaid diagram",
    )

    @field_validator("plantuml_jar_path", mode="before")
    @classmethod
    def _resolve_plantuml_path(cls, value: object) -> Path:
        if isinstance(value, str):
            return Path(value)
        return value  # type: ignore[return-value]
