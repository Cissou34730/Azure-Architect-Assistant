"""Cross-feature contract for project summaries."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ProjectSummaryContract(BaseModel):
    """Project metadata exposed across feature boundaries."""

    model_config = ConfigDict(populate_by_name=True)

    project_id: str = Field(alias="projectId")
    name: str
    description: str = ""
    created_at: str = Field(alias="createdAt")
    document_count: int = Field(alias="documentCount")
