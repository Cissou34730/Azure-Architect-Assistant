"""Shared schemas for diagram generation routers."""

from pydantic import BaseModel


class AmbiguityReportResponse(BaseModel):
    """Response model for ambiguity report."""

    id: str
    diagram_set_id: str
    ambiguous_text: str
    suggested_clarification: str | None = None
    resolved: bool = False
    created_at: str
