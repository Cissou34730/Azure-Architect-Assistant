"""Utility functions for extracting project state updates from agent responses."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def extract_state_updates(
    agent_response: str, user_message: str, current_state: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Infer partial `ProjectState` updates based on agent output and user input.

    This keeps the heuristic parsing logic out of the API router and allows reuse in
    other agent surfaces (e.g., batch processing, CLI tools) without duplicating code.
    The focus is on common non-functional requirement signals (availability, security,
    performance, cost). Returns ``None`` when no actionable updates are detected.
    """
    combined_text = f"{user_message} {agent_response}".lower()

    updates: Dict[str, Any] = {}

    availability_match = re.search(
        r"(\d{2,3}(?:\.\d+)?%)\s+(?:availability|uptime|sla)",
        combined_text,
        re.IGNORECASE,
    )
    if availability_match:
        updates.setdefault("nfrs", {})["availability"] = (
            f"{availability_match.group(1)} SLA requirement"
        )

    security_keywords = [
        "security",
        "authentication",
        "authorization",
        "encryption",
        "compliance",
    ]
    if any(keyword in user_message.lower() for keyword in security_keywords):
        existing_security = current_state.get("nfrs", {}).get("security")
        if not existing_security:
            security_mentions = [
                line.strip()
                for line in agent_response.split("\n")
                if any(kw in line.lower() for kw in security_keywords)
            ]
            if security_mentions:
                updates.setdefault("nfrs", {})["security"] = "; ".join(
                    security_mentions[:3]
                )

    perf_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(ms|seconds?|milliseconds?)\s+(?:latency|response time)",
        combined_text,
        re.IGNORECASE,
    )
    if perf_match:
        updates.setdefault("nfrs", {})["performance"] = (
            f"{perf_match.group(1)} {perf_match.group(2)} target"
        )

    if "cost" in combined_text or "budget" in combined_text:
        cost_match = re.search(r"\$[\d,]+(?:\.\d{2})?", combined_text)
        if cost_match:
            updates.setdefault("nfrs", {})["costConstraints"] = (
                f"Budget: {cost_match.group(0)}"
            )

    return updates or None


@dataclass(frozen=True)
class StateMergeConflict:
    path: str
    existing: Any
    incoming: Any
    reason: str = "overwrite_blocked"


@dataclass(frozen=True)
class StateMergeResult:
    merged_state: Dict[str, Any]
    conflicts: List[StateMergeConflict] = field(default_factory=list)


def merge_state_updates_no_overwrite(
    current_state: Dict[str, Any], updates: Dict[str, Any]
) -> StateMergeResult:
    """Merge updates into current state without overwriting existing values.

    Rules (minimal, generic primitives):
    - Scalars: if existing value is non-empty and differs, do NOT overwrite; record conflict.
    - Dicts: recurse per key.
    - Lists:
      - If list items are dicts with an `id`, merge by id recursively.
      - Otherwise, append new unique items (by equality).
    """
    merged_state: Dict[str, Any] = dict(current_state)
    conflicts: List[StateMergeConflict] = []
    _merge_into(merged_state, updates, conflicts, path="")
    return StateMergeResult(merged_state=merged_state, conflicts=conflicts)


def _is_missing(value: Any) -> bool:
    return value is None or value == ""


def _merge_into(
    base: Dict[str, Any],
    updates: Dict[str, Any],
    conflicts: List[StateMergeConflict],
    *,
    path: str,
) -> None:
    for key, incoming in updates.items():
        next_path = f"{path}.{key}" if path else str(key)

        if key not in base or _is_missing(base.get(key)):
            base[key] = incoming
            continue

        existing = base.get(key)

        if isinstance(existing, dict) and isinstance(incoming, dict):
            _merge_into(existing, incoming, conflicts, path=next_path)
            continue

        if isinstance(existing, list) and isinstance(incoming, list):
            _merge_lists(existing, incoming, conflicts, path=next_path)
            continue

        if existing == incoming:
            continue

        # Do not overwrite non-empty values
        if not _is_missing(incoming):
            conflicts.append(
                StateMergeConflict(path=next_path, existing=existing, incoming=incoming)
            )


def _merge_lists(
    existing_list: List[Any],
    incoming_list: List[Any],
    conflicts: List[StateMergeConflict],
    *,
    path: str,
) -> None:
    existing_id_index: Dict[str, Dict[str, Any]] = {}
    if all(isinstance(item, dict) and "id" in item for item in existing_list):
        for item in existing_list:
            existing_id_index[str(item["id"])] = item

    for item in incoming_list:
        if isinstance(item, dict) and "id" in item and existing_id_index:
            item_id = str(item["id"])
            existing_item = existing_id_index.get(item_id)
            if existing_item is None:
                existing_list.append(item)
                existing_id_index[item_id] = item
            else:
                _merge_into(existing_item, item, conflicts, path=f"{path}[id={item_id}]")
            continue

        if item not in existing_list:
            existing_list.append(item)
