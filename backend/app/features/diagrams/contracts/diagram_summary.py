"""Cross-feature contract for diagram summaries."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class DiagramSummaryContract(BaseModel):
    """Diagram summary exposed by the projects workspace view."""

    model_config = ConfigDict(populate_by_name=True)

    diagram_set_id: str = Field(alias="diagramSetId")
    diagram_types: list[str] = Field(default_factory=list, alias="diagramTypes")
