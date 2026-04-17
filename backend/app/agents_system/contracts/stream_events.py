"""Typed SSE payload contracts for project-chat streaming."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from .workflow_result import WorkflowStageResult

_STREAM_EVENT_CONFIG = ConfigDict(
    populate_by_name=True,
    alias_generator=to_camel,
    extra="allow",
)


class _StreamEventModel(BaseModel):
    model_config = _STREAM_EVENT_CONFIG


class StageStreamEventPayload(_StreamEventModel):
    stage: str
    confidence: float = Field(ge=0.0, le=1.0)


class ToolCallStreamEventPayload(_StreamEventModel):
    tool: str
    args_preview: str


class ToolResultStreamEventPayload(_StreamEventModel):
    tool: str
    result_preview: str
    citations: list[str] = Field(default_factory=list)
    tool_call_id: str | None = None
    content: str | None = None
    status: str | None = None


class TextStreamEventPayload(_StreamEventModel):
    delta: str


class PendingChangeStreamEventPayload(_StreamEventModel):
    change_set_id: str = Field(alias="changeSetId")
    summary: str
    patch_count: int = Field(alias="patchCount", ge=0)


class FinalStreamEventPayload(_StreamEventModel):
    answer: str
    success: bool
    project_state: dict[str, Any] | None = Field(default=None, alias="project_state")
    reasoning_steps: list[dict[str, Any]] = Field(
        default_factory=list,
        alias="reasoning_steps",
    )
    error: str | None = None
    thread_id: str | None = Field(default=None, alias="thread_id")
    workflow_result: WorkflowStageResult | None = Field(default=None, alias="workflow_result")


def serialize_sse_event(event: str, payload: BaseModel | dict[str, Any]) -> str:
    """Serialize a typed SSE event into wire format."""
    if isinstance(payload, BaseModel):
        serialized_payload = payload.model_dump(mode="json", by_alias=True, exclude_none=False)
    else:
        serialized_payload = payload
    data = json.dumps(serialized_payload, ensure_ascii=True)
    return f"event: {event}\ndata: {data}\n\n"
