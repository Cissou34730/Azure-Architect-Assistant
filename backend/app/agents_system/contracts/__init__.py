"""Structured contracts for LangGraph workflow outputs."""

from .stage_contracts import (
    AdrDraftOutput,
    ArchitectureDraftOutput,
    ClarificationPlanOutput,
    RequirementsExtractionOutput,
    ValidationOutput,
    _parse_and_validate_output,
)
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
    "AdrDraftOutput",
    "ArchitectChoiceOption",
    "ArchitectChoicePayload",
    "ArchitectureDraftOutput",
    "ClarificationPlanOutput",
    "ClarificationQuestionPayloadItem",
    "ClarificationQuestionsPayload",
    "FinalStreamEventPayload",
    "NextStepProposal",
    "PendingChangeStreamEventPayload",
    "RequirementsExtractionOutput",
    "StageClassification",
    "StageStreamEventPayload",
    "TextStreamEventPayload",
    "ToolCallStreamEventPayload",
    "ToolCallTrace",
    "ToolResultStreamEventPayload",
    "ValidationOutput",
    "WorkflowCitation",
    "WorkflowStageResult",
    "_parse_and_validate_output",
    "normalize_structured_payload",
    "serialize_sse_event",
]
