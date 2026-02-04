from pydantic import BaseModel, Field
from uuid import UUID
from typing import Literal, Optional
from datetime import datetime

class ChecklistSummary(BaseModel):
    id: UUID
    project_id: str
    template_id: Optional[UUID] = None
    title: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

class ChecklistItemDetail(BaseModel):
    id: UUID
    template_item_id: str
    title: str
    description: Optional[str] = None
    pillar: Optional[str] = None
    severity: str
    latest_status: str
    last_evaluated: Optional[str] = None

class ChecklistDetail(BaseModel):
    id: UUID
    project_id: str
    template_id: Optional[UUID] = None
    title: str
    status: str
    items: list[ChecklistItemDetail]

class EvaluateItemRequest(BaseModel):
    status: str
    evaluator: str = "user"
    evidence: Optional[dict] = None
    comment: Optional[str] = None
    source_type: str = "manual"

class ProgressResponse(BaseModel):
    total_items: int
    completed_items: int
    percent_complete: float
    severity_breakdown: dict[str, dict[str, int]]
    last_updated: str
    next_actions: list[dict]
