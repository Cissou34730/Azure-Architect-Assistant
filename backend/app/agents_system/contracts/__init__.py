"""Structured contracts for LangGraph workflow outputs."""

from .stream_events import (
    FinalStreamEventPayload,
    PendingChangeStreamEventPayload,
    StageStreamEventPayload,
    TextStreamEventPayload,
    ToolCallStreamEventPayload,
    ToolResultStreamEventPayload,
    serialize_sse_event,
)
from .workflow_result import (
    ArchitectChoiceOption,
    ArchitectChoicePayload,
    ClarificationQuestionPayloadItem,
    ClarificationQuestionsPayload,
    NextStepProposal,
    StageClassification,
    ToolCallTrace,
    WorkflowCitation,
    WorkflowStageResult,
    normalize_structured_payload,
)

__all__ = [
    "ArchitectChoiceOption",
    "ArchitectChoicePayload",
    "ClarificationQuestionPayloadItem",
    "ClarificationQuestionsPayload",
    "FinalStreamEventPayload",
    "NextStepProposal",
    "PendingChangeStreamEventPayload",
    "StageClassification",
    "StageStreamEventPayload",
    "TextStreamEventPayload",
    "ToolCallStreamEventPayload",
    "ToolCallTrace",
    "ToolResultStreamEventPayload",
    "WorkflowCitation",
    "WorkflowStageResult",
    "normalize_structured_payload",
    "serialize_sse_event",
]
