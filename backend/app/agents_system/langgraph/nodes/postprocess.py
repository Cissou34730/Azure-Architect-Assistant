"""
Post-processing nodes for LangGraph workflow.

Extracts state updates, derives MCP logs, and detects architect choice requirements.
"""

import logging
import re
from typing import Any

from app.agents_system.contracts import (
    ArchitectChoiceOption,
    ArchitectChoicePayload,
    normalize_structured_payload,
)
from app.agents_system.tools.tool_registry import normalize_pending_change_tool_result
from app.features.agent.application.pending_change_briefing_service import (
    PendingChangeBriefingService,
)
from app.features.projects.contracts import PendingChangeSetContract

from ...services.iteration_logging import (
    build_iteration_event_update,
    derive_mcp_query_updates_from_steps,
)
from ...services.state_update_parser import extract_state_updates
from ..state import GraphState

_briefing_service = PendingChangeBriefingService()

logger = logging.getLogger(__name__)

_AAA_STATE_UPDATE_MARKER = "AAA_STATE_UPDATE"
_ARCHITECT_CHOICE_MARKER_RE = re.compile(
    r"architect\s+choice\s+required\s*:", re.IGNORECASE
)
_ARCHITECT_OPTION_RE = re.compile(
    r"^\s*(?:[-*]|\d+[.)]|option\s+[a-z0-9]+[:.)-])\s+(?P<text>.+)$",
    re.IGNORECASE,
)


def _extract_architect_choice_required_section(text: str) -> str | None:
    """Extract architect choice required section from agent output."""
    if not text:
        return None

    match = _ARCHITECT_CHOICE_MARKER_RE.search(text)
    if not match:
        return None

    start = match.start()
    end = text.find(_AAA_STATE_UPDATE_MARKER, start)
    if end < 0:
        end = len(text)

    section = text[start:end].strip()
    if not section:
        return None

    # Avoid bloating ProjectState.openQuestions
    return section[:1500]


async def postprocess_node(state: GraphState, response_message_id: str) -> dict[str, Any]:
    """
    Post-process agent output to extract updates and detect architect choices.
    """
    agent_output = str(state.get("agent_output", ""))
    intermediate_steps = state.get("intermediate_steps", [])
    user_message = str(state.get("user_message", ""))
    current_project_state = state.get("current_project_state", {})

    # 1) Detect architect choice
    architect_choice_required = _extract_architect_choice_required_section(agent_output)
    if architect_choice_required:
        logger.warning("Architect choice required detected; will block state updates")
    structured_payload = _resolve_structured_payload(
        state.get("structured_payload"),
        architect_choice_required,
    )
    pending_change_set = _extract_pending_change_set(intermediate_steps)

    # P6: Generate architect briefing from pending change set
    generated_briefing = _generate_briefing_from_pending_change(pending_change_set)

    # 2) Extract and merge state updates
    state_updates = None
    if pending_change_set is None:
        state_updates = _extract_and_merge_state_updates(
            agent_output, intermediate_steps, user_message, current_project_state
        )

    # FR-018: Block state updates if architect choice is required
    if architect_choice_required:
        state_updates = None

    # 3) Derive MCP query logging
    derived_updates = derive_mcp_query_updates_from_steps(
        intermediate_steps=intermediate_steps,
        user_message=user_message,
    )

    # 4) Combine all updates
    combined_updates = _combine_final_updates(state_updates, derived_updates)

    # 5) Handle architect choice blocking and recording
    if architect_choice_required:
        combined_updates.setdefault("openQuestions", [])
        combined_updates["openQuestions"].append(architect_choice_required)

    # 6) Add iteration event
    _add_iteration_event(combined_updates, user_message, architect_choice_required, response_message_id)

    logger.info(
        f"Post-processing complete: combined_updates keys={sorted(combined_updates.keys())}"
    )

    return {
        "architect_choice_required_section": architect_choice_required,
        "generated_briefing": generated_briefing,
        "pending_change_set": pending_change_set,
        "structured_payload": structured_payload,
        "state_updates": state_updates,
        "derived_updates": derived_updates,
        "combined_updates": combined_updates,
    }


def _resolve_structured_payload(
    existing_payload: Any,
    architect_choice_required: str | None,
) -> dict[str, Any] | None:
    if architect_choice_required:
        return _build_architect_choice_structured_payload(architect_choice_required)
    return normalize_structured_payload(existing_payload) if existing_payload is not None else None


def _build_architect_choice_structured_payload(section: str) -> dict[str, Any]:
    lines = [line.strip() for line in section.splitlines() if line.strip()]
    if not lines:
        return ArchitectChoicePayload(prompt=section).model_dump(mode="json", by_alias=True)

    prompt_lines: list[str] = []
    options: list[ArchitectChoiceOption] = []
    for line in lines:
        marker_match = _ARCHITECT_CHOICE_MARKER_RE.search(line)
        if marker_match:
            prompt_text = line[marker_match.end() :].strip()
            if prompt_text:
                prompt_lines.append(prompt_text)
            continue

        option_match = _ARCHITECT_OPTION_RE.match(line)
        if option_match:
            option_text = option_match.group("text").strip()
            if option_text:
                options.append(
                    ArchitectChoiceOption(
                        id=f"option-{len(options) + 1}",
                        title=option_text,
                    )
                )
            continue

        if not options:
            prompt_lines.append(line)

    prompt = " ".join(prompt_lines).strip() or section.strip()
    return ArchitectChoicePayload(prompt=prompt, options=options).model_dump(
        mode="json",
        by_alias=True,
    )


def _extract_from_steps(
    steps: list[Any], user_message: str, project_state: dict[str, Any]
) -> list[dict[str, Any]]:
    """Extract state updates from intermediate tool observations."""
    extracted = []
    for _, observation in steps:
        if normalize_pending_change_tool_result(observation) is not None:
            continue
        if isinstance(observation, str) and _AAA_STATE_UPDATE_MARKER in observation:
            tool_u = extract_state_updates(observation, user_message, project_state)
            if tool_u:
                extracted.append(tool_u)
    return extracted


def _extract_pending_change_set(steps: list[Any]) -> dict[str, Any] | None:
    for _, observation in reversed(steps):
        canonical_result = normalize_pending_change_tool_result(observation)
        if canonical_result is None:
            continue
        return canonical_result.pending_change_set.model_dump(mode="json", by_alias=True)
    return None


def _generate_briefing_from_pending_change(
    pending_change_set: dict[str, Any] | None,
) -> str | None:
    """Generate an Architect Briefing from a pending change set dict, if present."""
    if not isinstance(pending_change_set, dict):
        return None
    try:
        cs = PendingChangeSetContract.model_validate(pending_change_set)
        return _briefing_service.generate_briefing(cs)
    except Exception:  # noqa: BLE001
        logger.warning("Failed to generate briefing from pending change set", exc_info=True)
        return None


def _merge_update_sets(update_sets: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge a list of state update dictionaries into a single combined update."""
    merged: dict[str, Any] = {}
    for update_set in update_sets:
        for key, value in update_set.items():
            if key not in merged:
                merged[key] = value
            elif isinstance(merged[key], list) and isinstance(value, list):
                merged[key] = [*merged[key], *value]
            else:
                merged[key] = value
    return merged


def _extract_and_merge_state_updates(
    agent_output: str,
    intermediate_steps: list[Any],
    user_message: str,
    current_project_state: dict[str, Any],
) -> dict[str, Any] | None:
    """Extract AAA_STATE_UPDATE blocks and merge them."""
    all_extracted: list[dict[str, Any]] = []

    # From agent output
    updates = extract_state_updates(agent_output, user_message, current_project_state)
    if updates:
        all_extracted.append(updates)

    # From tool results
    all_extracted.extend(
        _extract_from_steps(intermediate_steps, user_message, current_project_state)
    )

    if not all_extracted:
        return None

    return _merge_update_sets(all_extracted)


def _combine_final_updates(
    state_updates: dict[str, Any] | None,
    derived_updates: dict[str, Any] | None
) -> dict[str, Any]:
    """Combine state updates with derived updates (MCP logs, etc)."""
    combined: dict[str, Any] = {}
    sources = [s for s in [state_updates, derived_updates] if s is not None]

    for src in sources:
        for key, value in src.items():
            if key not in combined:
                combined[key] = value
                continue
            if isinstance(combined[key], list) and isinstance(value, list):
                combined[key] = [*combined[key], *value]
            elif isinstance(combined[key], dict) and isinstance(value, dict):
                combined[key] = {**combined[key], **value}

    return combined


def _determine_iteration_kind(user_message: str) -> str:
    """Determine the kind of iteration based on user message content."""
    user_msg_lower = user_message.lower()
    keywords = ["validate", "validation", "waf", "risk", "security benchmark"]
    if any(k in user_msg_lower for k in keywords):
        return "challenge"
    return "propose"


def _add_iteration_event(
    combined_updates: dict[str, Any],
    user_message: str,
    architect_choice_required: str | None,
    response_message_id: str,
) -> None:
    """Add an iteration event to the combined updates."""
    mcp_query_ids = [
        str(q.get("id"))
        for q in combined_updates.get("mcpQueries", [])
        if isinstance(q, dict) and q.get("id")
    ]

    event_update = build_iteration_event_update(
        kind=_determine_iteration_kind(user_message),
        text=architect_choice_required
        or "Agent processed request and refined architecture artifacts.",
        mcp_query_ids=mcp_query_ids,
        architect_response_message_id=response_message_id,
    )

    if not event_update:
        return

    for key, value in event_update.items():
        if key not in combined_updates:
            combined_updates[key] = value
        elif isinstance(combined_updates[key], list) and isinstance(value, list):
            combined_updates[key] = [*combined_updates[key], *value]

