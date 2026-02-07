"""Pydantic schemas for normalized checklist API endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ChecklistSummary(BaseModel):
    id: UUID
    project_id: str
    template_id: UUID | None = None
    template_slug: str | None = None
    title: str
    version: str | None = None
    status: str
    items_count: int = 0
    last_synced_at: datetime | None = None


class ChecklistItemLatestEvaluation(BaseModel):
    status: str
    evaluator: str
    timestamp: datetime | None = None


class ChecklistItemDetail(BaseModel):
    id: UUID
    template_item_id: str
    title: str
    description: str | None = None
    pillar: str | None = None
    severity: str
    guidance: dict[str, Any] | None = None
    item_metadata: dict[str, Any] | None = None
    latest_evaluation: ChecklistItemLatestEvaluation | None = None


class ChecklistDetail(ChecklistSummary):
    items: list[ChecklistItemDetail]


class EvaluateItemRequest(BaseModel):
    status: str
    evaluator: str = Field(default="user")
    evidence: dict[str, Any] | str | None = None
    comment: str | None = None
    source_type: str = Field(default="manual")
    source_id: str | None = None


class EvaluateItemResponse(BaseModel):
    status: str
    evaluation_id: str


class ProgressResponse(BaseModel):
    total_items: int
    completed_items: int
    percent_complete: float
    severity_breakdown: dict[str, dict[str, int]]
    status_breakdown: dict[str, int]
    next_actions: list[dict[str, Any]]
    last_updated: str


class ResyncResponse(BaseModel):
    status: str
    items_synced: int = 0
    evaluations_synced: int = 0
    errors: list[str] = Field(default_factory=list)
