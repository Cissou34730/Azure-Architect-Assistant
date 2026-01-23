"""
Post-processing nodes for LangGraph workflow.

Extracts state updates, derives MCP logs, and detects architect choice requirements.
"""

import logging
import re
from typing import Any

from ...services.iteration_logging import (
    build_iteration_event_update,
    derive_mcp_query_updates_from_steps,
)
from ...services.state_update_parser import extract_state_updates
from ..state import GraphState

logger = logging.getLogger(__name__)

_AAA_STATE_UPDATE_MARKER = "AAA_STATE_UPDATE"
_ARCHITECT_CHOICE_MARKER_RE = re.compile(
    r"architect\s+choice\s+required\s*:", re.IGNORECASE
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

    # 2) Extract and merge state updates
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
        "state_updates": state_updates,
        "derived_updates": derived_updates,
        "combined_updates": combined_updates,
    }


def _extract_from_steps(
    steps: list[Any], user_message: str, project_state: dict[str, Any]
) -> list[dict[str, Any]]:
    """Extract state updates from intermediate tool observations."""
    extracted = []
    for _, observation in steps:
        if isinstance(observation, str) and _AAA_STATE_UPDATE_MARKER in observation:
            tool_u = extract_state_updates(observation, user_message, project_state)
            if tool_u:
                extracted.append(tool_u)
    return extracted


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

