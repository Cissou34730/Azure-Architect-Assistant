"""Canonical tool registry for stage-specific pending-change persistence."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.agents_system.langgraph.nodes.stage_routing import ProjectStage
from app.features.projects.application.chat_service import ChatService
from app.features.projects.application.pending_changes_service import (
    ProjectPendingChangesService,
)
from app.features.projects.contracts import (
    ArtifactDraftType,
    ChangeSetStatus,
    PendingChangeSetContract,
)

_TOOL_RESULT_CONFIG = ConfigDict(
    populate_by_name=True,
    alias_generator=to_camel,
    extra="forbid",
)

_STATE_UPDATE_MARKER = "AAA_STATE_UPDATE"


class PendingChangeToolResult(BaseModel):
    """Canonical tool result for persisted pending changes."""

    model_config = _TOOL_RESULT_CONFIG

    type: Literal["pending_change_confirmation"] = "pending_change_confirmation"
    tool_name: str
    stage: str
    message: str
    pending_change_set: PendingChangeSetContract


@dataclass(frozen=True)
class RegisteredToolDefinition:
    name: str
    stages: frozenset[str]
    fallback_stage: str


@dataclass(frozen=True)
class ToolRuntimeContext:
    project_id: str | None = None
    stage: str | None = None
    db: Any | None = None
    source_message_id: str | None = None


@dataclass(frozen=True)
class RegisteredRuntimeToolDefinition:
    name: str
    stages: frozenset[str]


_REGISTERED_TOOL_DEFINITIONS: dict[str, RegisteredToolDefinition] = {
    "aaa_generate_candidate_architecture": RegisteredToolDefinition(
        name="aaa_generate_candidate_architecture",
        stages=frozenset({ProjectStage.GENERAL.value, ProjectStage.PROPOSE_CANDIDATE.value}),
        fallback_stage=ProjectStage.PROPOSE_CANDIDATE.value,
    ),
    "aaa_manage_adr": RegisteredToolDefinition(
        name="aaa_manage_adr",
        stages=frozenset({ProjectStage.GENERAL.value, ProjectStage.MANAGE_ADR.value}),
        fallback_stage=ProjectStage.MANAGE_ADR.value,
    ),
    "aaa_manage_artifacts": RegisteredToolDefinition(
        name="aaa_manage_artifacts",
        stages=frozenset({ProjectStage.GENERAL.value, ProjectStage.PROPOSE_CANDIDATE.value}),
        fallback_stage=ProjectStage.GENERAL.value,
    ),
    "aaa_create_diagram_set": RegisteredToolDefinition(
        name="aaa_create_diagram_set",
        stages=frozenset({ProjectStage.GENERAL.value, ProjectStage.PROPOSE_CANDIDATE.value}),
        fallback_stage=ProjectStage.PROPOSE_CANDIDATE.value,
    ),
    "aaa_record_validation_results": RegisteredToolDefinition(
        name="aaa_record_validation_results",
        stages=frozenset({ProjectStage.GENERAL.value, ProjectStage.VALIDATE.value}),
        fallback_stage=ProjectStage.VALIDATE.value,
    ),
    "aaa_record_iac_artifacts": RegisteredToolDefinition(
        name="aaa_record_iac_artifacts",
        stages=frozenset({ProjectStage.GENERAL.value, ProjectStage.IAC.value}),
        fallback_stage=ProjectStage.IAC.value,
    ),
    "aaa_record_cost_estimate": RegisteredToolDefinition(
        name="aaa_record_cost_estimate",
        stages=frozenset({ProjectStage.GENERAL.value, ProjectStage.PRICING.value}),
        fallback_stage=ProjectStage.PRICING.value,
    ),
}

_ALL_REGISTERED_TOOL_NAMES = frozenset(_REGISTERED_TOOL_DEFINITIONS)

_REGISTERED_RUNTIME_TOOL_DEFINITIONS: dict[str, RegisteredRuntimeToolDefinition] = {
    "azure_retail_prices": RegisteredRuntimeToolDefinition(
        name="azure_retail_prices",
        stages=frozenset({ProjectStage.GENERAL.value, ProjectStage.PRICING.value}),
    ),
    "aaa_validate_mermaid_diagram": RegisteredRuntimeToolDefinition(
        name="aaa_validate_mermaid_diagram",
        stages=frozenset(
            {
                ProjectStage.GENERAL.value,
                ProjectStage.PROPOSE_CANDIDATE.value,
                ProjectStage.VALIDATE.value,
            }
        ),
    ),
    "aaa_validate_iac_bundle": RegisteredRuntimeToolDefinition(
        name="aaa_validate_iac_bundle",
        stages=frozenset({ProjectStage.GENERAL.value, ProjectStage.IAC.value}),
    ),
}

_ALL_REGISTERED_RUNTIME_TOOL_NAMES = frozenset(_REGISTERED_RUNTIME_TOOL_DEFINITIONS)

_ARTIFACT_TYPE_BY_STATE_KEY: dict[str, ArtifactDraftType] = {
    "requirements": ArtifactDraftType.REQUIREMENT,
    "assumptions": ArtifactDraftType.ASSUMPTION,
    "clarificationQuestions": ArtifactDraftType.CLARIFICATION_QUESTION,
    "candidateArchitectures": ArtifactDraftType.CANDIDATE_ARCHITECTURE,
    "adrs": ArtifactDraftType.ADR,
    "findings": ArtifactDraftType.FINDING,
    "diagrams": ArtifactDraftType.DIAGRAM,
    "iacArtifacts": ArtifactDraftType.IAC,
    "costEstimates": ArtifactDraftType.COST_ESTIMATE,
    "wafChecklist": ArtifactDraftType.WAF_UPDATE,
}

_SUMMARY_LABELS: dict[str, str] = {
    "requirements": "requirement draft",
    "assumptions": "assumption draft",
    "clarificationQuestions": "clarification question draft",
    "candidateArchitectures": "candidate architecture draft",
    "adrs": "ADR draft",
    "findings": "validation finding",
    "diagrams": "diagram draft",
    "iacArtifacts": "IaC artifact bundle",
    "costEstimates": "cost estimate",
    "wafChecklist": "WAF checklist update",
}


def get_allowed_pending_change_tool_names(stage: str | None) -> frozenset[str]:
    """Return registered pending-change tools allowed for a stage."""
    if not stage:
        return _ALL_REGISTERED_TOOL_NAMES
    allowed = {
        name
        for name, definition in _REGISTERED_TOOL_DEFINITIONS.items()
        if stage in definition.stages
    }
    return frozenset(allowed or _ALL_REGISTERED_TOOL_NAMES)


def normalize_pending_change_tool_result(observation: Any) -> PendingChangeToolResult | None:
    """Validate a canonical pending-change tool observation."""
    if isinstance(observation, PendingChangeToolResult):
        return observation
    if isinstance(observation, dict):
        try:
            return PendingChangeToolResult.model_validate(observation)
        except Exception:  # noqa: BLE001
            return None
    return None


def get_allowed_runtime_tool_names(stage: str | None) -> frozenset[str]:
    """Return registered runtime tools allowed for a stage."""
    if not stage:
        return _ALL_REGISTERED_RUNTIME_TOOL_NAMES
    allowed = {
        name
        for name, definition in _REGISTERED_RUNTIME_TOOL_DEFINITIONS.items()
        if stage in definition.stages
    }
    return frozenset(allowed)


async def maybe_persist_tool_result(
    *,
    tool_name: str,
    raw_result: Any,
    runtime_context: ToolRuntimeContext | None,
) -> Any:
    """Persist registered tool outputs as canonical pending-change confirmations."""
    definition = _REGISTERED_TOOL_DEFINITIONS.get(tool_name)
    if (
        definition is None
        or runtime_context is None
        or not runtime_context.project_id
        or runtime_context.db is None
    ):
        return raw_result

    existing_result = normalize_pending_change_tool_result(raw_result)
    if existing_result is not None:
        return existing_result.model_dump(mode="json", by_alias=True)

    updates = _extract_update_payload(raw_result)
    if updates is None:
        return raw_result

    stage_value = (
        runtime_context.stage
        if runtime_context.stage in definition.stages
        else definition.fallback_stage
    )
    change_set = _build_pending_change_set(
        tool_name=tool_name,
        project_id=runtime_context.project_id,
        stage=stage_value,
        source_message_id=runtime_context.source_message_id,
        updates=updates,
    )
    service = ProjectPendingChangesService(state_provider=ChatService())
    recorded_change_set = await service.record_pending_change(
        project_id=runtime_context.project_id,
        change_set=change_set,
        db=runtime_context.db,
    )
    canonical_result = PendingChangeToolResult(
        tool_name=tool_name,
        stage=stage_value,
        message=(
            f"Created pending change set `{recorded_change_set.id}`. "
            "Review and approve it before merging the draft into project state."
        ),
        pending_change_set=recorded_change_set,
    )
    return canonical_result.model_dump(mode="json", by_alias=True)


def _extract_update_payload(raw_result: Any) -> dict[str, Any] | None:
    if isinstance(raw_result, dict):
        return _extract_update_payload_from_mapping(raw_result)
    if not isinstance(raw_result, str):
        return None
    return _extract_update_payload_from_text(raw_result)


def _extract_update_payload_from_mapping(raw_result: dict[str, Any]) -> dict[str, Any] | None:
    pending_change_result = normalize_pending_change_tool_result(raw_result)
    if pending_change_result is not None:
        return pending_change_result.pending_change_set.proposed_patch
    if all(isinstance(key, str) for key in raw_result):
        return dict(raw_result)
    return None


def _extract_update_payload_from_text(raw_result: str) -> dict[str, Any] | None:
    marker_index = raw_result.find(_STATE_UPDATE_MARKER)
    if marker_index < 0:
        return None

    after_marker = raw_result[marker_index + len(_STATE_UPDATE_MARKER) :]
    fence_start = after_marker.find("```json")
    if fence_start < 0:
        return None
    json_body = after_marker[fence_start + len("```json") :]
    fence_end = json_body.find("```")
    if fence_end < 0:
        return None

    try:
        parsed = json.loads(json_body[:fence_end].strip())
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _build_pending_change_set(
    *,
    tool_name: str,
    project_id: str,
    stage: str,
    source_message_id: str | None,
    updates: dict[str, Any],
) -> PendingChangeSetContract:
    created_at = datetime.now(timezone.utc).isoformat()
    return PendingChangeSetContract(
        id=f"pcs-{uuid.uuid4()}",
        projectId=project_id,
        stage=stage,
        status=ChangeSetStatus.PENDING,
        createdAt=created_at,
        sourceMessageId=source_message_id,
        bundleSummary=_build_bundle_summary(tool_name=tool_name, updates=updates),
        proposedPatch=updates,
        artifactDrafts=_build_artifact_drafts(updates=updates, created_at=created_at),
    )


def _build_bundle_summary(*, tool_name: str, updates: dict[str, Any]) -> str:
    parts: list[str] = []
    for key, label in _SUMMARY_LABELS.items():
        count = _item_count_for_summary(key=key, value=updates.get(key))
        if count:
            plural_suffix = "" if count == 1 else "s"
            parts.append(f"{count} {label}{plural_suffix}")
    if parts:
        return "Drafted " + ", ".join(parts)
    return f"Drafted pending changes via {tool_name}"


def _item_count_for_summary(*, key: str, value: Any) -> int:
    if key == "wafChecklist" and isinstance(value, dict):
        items = value.get("items")
        return len(items) if isinstance(items, list) else 0
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        return 1
    return 0


def _build_artifact_drafts(*, updates: dict[str, Any], created_at: str) -> list[dict[str, Any]]:
    drafts: list[dict[str, Any]] = []
    for key, artifact_type in _ARTIFACT_TYPE_BY_STATE_KEY.items():
        value = updates.get(key)
        for content in _iterate_artifact_contents(key=key, value=value):
            drafts.append(
                {
                    "id": str(uuid.uuid4()),
                    "artifactType": artifact_type.value,
                    "artifactId": _resolve_artifact_id(content),
                    "content": content,
                    "citations": _resolve_citations(content),
                    "createdAt": created_at,
                }
            )
    return drafts


def _iterate_artifact_contents(*, key: str, value: Any) -> list[dict[str, Any]]:
    if key == "wafChecklist" and isinstance(value, dict):
        items = value.get("items")
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
        return []
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [value]
    return []


def _resolve_artifact_id(content: dict[str, Any]) -> str | None:
    item_id = content.get("id")
    if item_id is None:
        return None
    return str(item_id)


def _resolve_citations(content: dict[str, Any]) -> list[dict[str, Any]]:
    citations = content.get("sourceCitations")
    if isinstance(citations, list):
        return [item for item in citations if isinstance(item, dict)]
    return []


__all__ = [
    "PendingChangeToolResult",
    "ToolRuntimeContext",
    "get_allowed_pending_change_tool_names",
    "get_allowed_runtime_tool_names",
    "maybe_persist_tool_result",
    "normalize_pending_change_tool_result",
]
