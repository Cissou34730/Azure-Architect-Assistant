"""Utility functions for extracting project state updates from agent responses."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

_AAA_UPDATE_MARKER = "AAA_STATE_UPDATE"


def _extract_json_code_block(text: str, *, marker: str) -> dict[str, Any] | None:
    """Extract a JSON code block that appears after a marker line.

    Expected format:
      AAA_STATE_UPDATE
      ```json
      { ... }
      ```
    """
    marker_index = text.find(marker)
    if marker_index < 0:
        return None

    after = text[marker_index + len(marker) :]
    fence_start = after.find("```json")
    if fence_start < 0:
        return None
    after = after[fence_start + len("```json") :]

    fence_end = after.find("```")
    if fence_end < 0:
        return None

    json_text = after[:fence_end].strip()
    if not json_text:
        return None

    try:
        payload = json.loads(json_text)
    except json.JSONDecodeError:
        return None

    return payload if isinstance(payload, dict) else None


def extract_state_updates(
    agent_response: str, user_message: str, current_state: dict[str, Any]
) -> dict[str, Any] | None:
    """Infer partial `ProjectState` updates based on agent output and user input."""
    # Priority 1: Structured JSON updates
    structured_updates = _extract_json_code_block(agent_response, marker=_AAA_UPDATE_MARKER)
    if structured_updates:
        return structured_updates

    # Priority 2: Heuristic inference from free text
    combined_text = f"{user_message} {agent_response}".lower()
    updates: dict[str, Any] = {}

    _infer_from_availability(combined_text, updates)
    _infer_from_security(user_message, agent_response, current_state, updates)
    _infer_from_performance(combined_text, updates)
    _infer_from_cost(combined_text, updates)

    return updates or None


def _infer_from_availability(text: str, updates: dict[str, Any]) -> None:
    """Detect availability SLA requirements."""
    match = re.search(r"(\d{2,3}(?:\.\d+)?%)\s+(?:availability|uptime|sla)", text, re.IGNORECASE)
    if match:
        updates.setdefault("nfrs", {})["availability"] = f"{match.group(1)} SLA requirement"


def _infer_from_security(
    user_msg: str, agent_resp: str, current_state: dict[str, Any], updates: dict[str, Any]
) -> None:
    """Detect security requirements."""
    security_keywords = ["security", "authentication", "authorization", "encryption", "compliance"]
    if any(keyword in user_msg.lower() for keyword in security_keywords):
        existing_security = current_state.get("nfrs", {}).get("security")
        if not existing_security:
            security_mentions = [
                line.strip()
                for line in agent_resp.split("\n")
                if any(kw in line.lower() for kw in security_keywords)
            ]
            if security_mentions:
                updates.setdefault("nfrs", {})["security"] = "; ".join(security_mentions[:3])


def _infer_from_performance(text: str, updates: dict[str, Any]) -> None:
    """Detect performance latency requirements."""
    match = re.search(
        r"(\d+(?:\.\d+)?)\s*(ms|seconds?|milliseconds?)\s+(?:latency|response time)",
        text,
        re.IGNORECASE,
    )
    if match:
        updates.setdefault("nfrs", {})["performance"] = f"{match.group(1)} {match.group(2)} target"


def _infer_from_cost(text: str, updates: dict[str, Any]) -> None:
    """Detect cost/budget constraints."""
    if "cost" in text or "budget" in text:
        match = re.search(r"\$[\d,]+(?:\.\d{2})?", text)
        if match:
            updates.setdefault("nfrs", {})["costConstraints"] = f"Budget: {match.group(0)}"


@dataclass(frozen=True)
class StateMergeConflict:
    path: str
    existing: Any
    incoming: Any
    reason: str = "overwrite_blocked"


@dataclass(frozen=True)
class StateMergeResult:
    merged_state: dict[str, Any]
    conflicts: list[StateMergeConflict] = field(default_factory=list)


def merge_state_updates_no_overwrite(
    current_state: dict[str, Any], updates: dict[str, Any]
) -> StateMergeResult:
    """Merge updates into current state without overwriting existing values.

    Rules (minimal, generic primitives):
    - Scalars: if existing value is non-empty and differs, do NOT overwrite; record conflict.
    - Dicts: recurse per key.
    - Lists:
      - If list items are dicts with an `id`, merge by id recursively.
      - Otherwise, append new unique items (by equality).
    """
    merged_state: dict[str, Any] = dict(current_state)
    conflicts: list[StateMergeConflict] = []
    _merge_into(merged_state, updates, conflicts, path="")
    return StateMergeResult(merged_state=merged_state, conflicts=conflicts)


def _is_missing(value: Any) -> bool:
    return value is None or value == ""


def _handle_type_merge(
    base: dict[str, Any],
    key: str,
    incoming: Any,
    conflicts: list[StateMergeConflict],
    next_path: str,
) -> bool:
    """Handle recursive merging for dicts and lists if types match."""
    existing = base.get(key)

    if isinstance(existing, dict) and isinstance(incoming, dict):
        _merge_into(existing, incoming, conflicts, path=next_path)
        return True

    if isinstance(existing, list) and isinstance(incoming, list):
        _merge_lists(existing, incoming, conflicts, path=next_path)
        return True

    return False


def _merge_into(
    base: dict[str, Any],
    updates: dict[str, Any],
    conflicts: list[StateMergeConflict],
    *,
    path: str,
) -> None:
    for key, incoming in updates.items():
        next_path = f"{path}.{key}" if path else str(key)

        if key not in base or _is_missing(base.get(key)):
            base[key] = incoming
            continue

        if _handle_type_merge(base, key, incoming, conflicts, next_path):
            continue

        existing = base.get(key)
        if existing == incoming or _is_missing(incoming):
            continue

        # Do not overwrite non-empty values
        conflicts.append(
            StateMergeConflict(path=next_path, existing=existing, incoming=incoming)
        )


def _merge_list_item(
    existing_list: list[Any],
    item: Any,
    existing_id_index: dict[str, dict[str, Any]],
    conflicts: list[StateMergeConflict],
    path: str,
) -> None:
    """Merge a single incoming list item into the existing list."""
    item_id = (
        str(item.get("id")) if isinstance(item, dict) and "id" in item else None
    )

    if item_id and existing_id_index:
        existing_item = existing_id_index.get(item_id)
        if existing_item is None:
            existing_list.append(item)
            existing_id_index[item_id] = item
        else:
            _merge_into(existing_item, item, conflicts, path=f"{path}[id={item_id}]")
        return

    if item not in existing_list:
        existing_list.append(item)


def _merge_lists(
    existing_list: list[Any],
    incoming_list: list[Any],
    conflicts: list[StateMergeConflict],
    *,
    path: str,
) -> None:
    existing_id_index: dict[str, dict[str, Any]] = {}
    if all(isinstance(item, dict) and "id" in item for item in existing_list):
        for item in existing_list:
            existing_id_index[str(item["id"])] = item

    for item in incoming_list:
        _merge_list_item(existing_list, item, existing_id_index, conflicts, path)

