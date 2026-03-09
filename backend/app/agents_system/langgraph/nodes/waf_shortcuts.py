"""Deterministic WAF-checklist shortcut handlers.

These bypass the LLM for explicit bulk/single-item checklist updates.
"""

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from ..state import GraphState
from .scope_guard import extract_target_pillar

_MIN_TOKEN_LENGTH = 2
_MIN_MATCH_SCORE = 0.6


def build_direct_waf_bulk_update_response(state: GraphState) -> dict[str, Any] | None:
    """Build deterministic checklist updates for explicit bulk-completion commands."""
    user_message = str(state.get("user_message", ""))

    target_pillar = extract_target_pillar(user_message)
    if target_pillar is None:
        return None
    if not _is_bulk_completion_request(user_message):
        return None

    items = _extract_pillar_items(state.get("current_project_state") or {}, target_pillar)
    if not items:
        return None

    timestamp = datetime.now(timezone.utc).isoformat()
    bulk_evidence = (
        f"Manual bulk override requested by user: marked all {target_pillar} checks as fixed. "
        "Evidence not independently verified in this turn."
    )
    update_items = [
        {
            "id": item["id"],
            "pillar": target_pillar,
            "topic": item["topic"],
            "evaluations": [
                {
                    "id": str(uuid.uuid4()),
                    "status": "fixed",
                    "evidence": bulk_evidence,
                    "relatedFindingIds": [],
                    "sourceCitations": [],
                    "createdAt": timestamp,
                }
            ],
        }
        for item in items
    ]
    state_update = {"wafChecklist": {"items": update_items}}
    response_text = (
        f"Updated {len(update_items)} {target_pillar} WAF checklist items to fixed.\n\n"
        "Risk warning: this is a manual bulk override without per-item validation evidence. "
        "Treat it as provisional and verify each control before sign-off.\n\n"
        "AAA_STATE_UPDATE\n"
        "```json\n"
        f"{json.dumps(state_update, ensure_ascii=False, indent=2)}\n"
        "```"
    )
    return {
        "agent_output": response_text,
        "intermediate_steps": [],
        "success": True,
        "error": None,
    }


def build_direct_waf_single_item_update_response(state: GraphState) -> dict[str, Any] | None:
    """Build deterministic checklist update for explicit single-item status commands."""
    user_message = str(state.get("user_message", ""))
    if not _is_single_item_update_request(user_message):
        return None

    target_status = _extract_target_status(user_message)
    if target_status is None:
        return None

    target_pillar = extract_target_pillar(user_message)
    items = _extract_pillar_items(state.get("current_project_state") or {}, target_pillar)
    if not items:
        return None

    matched_item = _match_single_item_from_message(user_message, items)
    if matched_item is None:
        return None

    timestamp = datetime.now(timezone.utc).isoformat()
    update_item = {
        "id": matched_item["id"],
        "pillar": matched_item["pillar"],
        "topic": matched_item["topic"],
        "evaluations": [
            {
                "id": str(uuid.uuid4()),
                "status": target_status,
                "evidence": (
                    f"Manual checklist update requested by user for topic '{matched_item['topic']}'. "
                    "Evidence not independently verified in this turn."
                ),
                "relatedFindingIds": [],
                "sourceCitations": [],
                "createdAt": timestamp,
            }
        ],
    }
    state_update = {"wafChecklist": {"items": [update_item]}}
    status_label = _status_to_label(target_status)
    response_text = (
        f"Updated '{matched_item['topic']}' ({matched_item['pillar']}) to {status_label}.\n\n"
        "Risk warning: this is a manual status override without per-item validation evidence. "
        "Treat it as provisional until evidence is captured.\n\n"
        "AAA_STATE_UPDATE\n"
        "```json\n"
        f"{json.dumps(state_update, ensure_ascii=False, indent=2)}\n"
        "```"
    )
    return {
        "agent_output": response_text,
        "intermediate_steps": [],
        "success": True,
        "error": None,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _is_bulk_completion_request(user_message: str) -> bool:
    lowered = user_message.lower()
    completion_terms = ("done", "complete", "completed", "covered", "green")
    scope_terms = ("all", "entire", "every")
    action_terms = ("update", "mark", "set")

    has_completion = any(term in lowered for term in completion_terms)
    has_scope = any(term in lowered for term in scope_terms)
    if not has_completion or not has_scope:
        return False

    has_checklist_ref = "checklist" in lowered or "waf" in lowered
    has_action = any(term in lowered for term in action_terms)
    return has_checklist_ref or has_action


def _is_single_item_update_request(user_message: str) -> bool:
    lowered = user_message.lower()
    has_checklist_ref = "checklist" in lowered or "waf" in lowered
    if not has_checklist_ref:
        return False

    if any(term in lowered for term in (" all ", " every ", " entire ")):
        return False

    action_terms = (
        "uncheck",
        "check",
        "mark",
        "set",
        "update",
        "not covered",
        "covered",
        "partial",
        "in progress",
    )
    return any(term in lowered for term in action_terms)


def _extract_target_status(user_message: str) -> str | None:
    lowered = user_message.lower()

    not_covered_terms = ("uncheck", "not covered", "not-covered", "remove check", "undo")
    partial_terms = ("partial", "in progress", "in-progress")
    covered_terms = ("check", "covered", "done", "complete", "completed", "green")

    if any(term in lowered for term in not_covered_terms):
        return "open"
    if any(term in lowered for term in partial_terms):
        return "in_progress"
    if any(term in lowered for term in covered_terms):
        return "fixed"
    return None


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value.lower())).strip()


def _topic_tokens(topic: str) -> list[str]:
    stopwords = {
        "the",
        "and",
        "for",
        "your",
        "with",
        "that",
        "this",
        "from",
        "into",
        "workload",
        "design",
        "checklist",
    }
    tokens = [token for token in _normalize_text(topic).split(" ") if len(token) > _MIN_TOKEN_LENGTH]
    return [token for token in tokens if token not in stopwords]


def _match_single_item_from_message(
    user_message: str,
    items: list[dict[str, str]],
) -> dict[str, str] | None:
    normalized_message = _normalize_text(user_message)
    best_match: dict[str, str] | None = None
    best_score = 0.0

    for item in items:
        topic = item["topic"]
        normalized_topic = _normalize_text(topic)
        if normalized_topic and normalized_topic in normalized_message:
            return item

        tokens = _topic_tokens(topic)
        if not tokens:
            continue

        overlap = sum(1 for token in tokens if token in normalized_message)
        score = overlap / len(tokens)
        if score > best_score:
            best_score = score
            best_match = item

    return best_match if best_score >= _MIN_MATCH_SCORE else None


def _status_to_label(status: str) -> str:
    if status == "open":
        return "open"
    if status == "in_progress":
        return "in progress"
    return "fixed"


def _extract_pillar_items(
    current_project_state: dict[str, Any], pillar: str | None
) -> list[dict[str, str]]:
    waf = current_project_state.get("wafChecklist")
    if not isinstance(waf, dict):
        return []

    raw_items = waf.get("items")
    if isinstance(raw_items, dict):
        items_iterable: list[Any] = list(raw_items.values())
    elif isinstance(raw_items, list):
        items_iterable = raw_items
    elif isinstance(raw_items, tuple):
        items_iterable = list(raw_items)
    else:
        return []

    selected: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for item in items_iterable:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id", "")).strip()
        topic = str(item.get("topic") or item.get("title") or item_id).strip()
        item_pillar = str(item.get("pillar", "")).strip()
        if not item_id or not topic:
            continue
        if pillar is not None and item_pillar.lower() != pillar.lower():
            continue
        if item_id in seen_ids:
            continue
        seen_ids.add(item_id)
        selected.append({"id": item_id, "topic": topic, "pillar": item_pillar or "General"})
    return selected
