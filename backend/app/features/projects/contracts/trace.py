"""Contracts for project trace timelines."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _TraceModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class ProjectTraceEventContract(_TraceModel):
    id: str
    project_id: str = Field(alias="projectId")
    thread_id: str | None = Field(default=None, alias="threadId")
    event_type: str = Field(alias="eventType")
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(alias="createdAt")


class ProjectTraceEventsResponse(_TraceModel):
    events: list[ProjectTraceEventContract] = Field(default_factory=list)
