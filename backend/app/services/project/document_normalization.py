"""Pure data-transformation helpers for AAA requirements & questions normalization.

These are stateless functions (no DB, no IO) extracted from DocumentService
to keep the service focused on orchestration.
"""

from __future__ import annotations

import uuid
from typing import Any


def normalize_aaa_requirements_and_questions(state_data: dict[str, Any]) -> None:
    """Ensure AAA requirements/questions exist and have stable IDs.

    This keeps the state aligned to the AAA data model (specs/002-azure-architect-assistant/data-model.md)
    without relying on the LLM to generate UUIDs.
    """
    _normalize_requirements(state_data)
    _normalize_questions(state_data)


def _normalize_requirements(state_data: dict[str, Any]) -> None:
    """Normalize requirements list."""
    requirements: list[dict[str, Any]] = []
    raw_requirements = state_data.get("requirements", []) or []

    for item in raw_requirements:
        normalized = _normalize_single_requirement(item)
        if normalized:
            requirements.append(normalized)

    # Preserve existing requirements if already present
    if not state_data.get("requirements"):
        state_data["requirements"] = requirements
    else:
        existing_reqs = state_data.get("requirements", [])
        if isinstance(existing_reqs, list):
            for r in existing_reqs:
                if isinstance(r, dict) and not r.get("id"):
                    r["id"] = str(uuid.uuid4())


def _extract_category(item: dict[str, Any]) -> str:
    """Extract and normalize requirement category."""
    category = (item.get("category") or "").strip().lower()
    return category if category in {"business", "functional", "nfr"} else "functional"


def _extract_ambiguity(item: dict[str, Any]) -> dict[str, Any]:
    """Extract and normalize requirement ambiguity info."""
    ambiguity_raw = item.get("ambiguity")
    ambiguity = ambiguity_raw if isinstance(ambiguity_raw, dict) else {}
    is_ambiguous = bool(ambiguity.get("isAmbiguous", False))
    notes = (ambiguity.get("notes") or "").strip()

    if is_ambiguous or notes:
        return {"isAmbiguous": is_ambiguous, "notes": notes}
    return {"isAmbiguous": False}


def _extract_sources(item: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract and normalize requirement sources."""
    sources_raw = item.get("sources")
    sources = sources_raw if isinstance(sources_raw, list) else []
    normalized_sources: list[dict[str, Any]] = []

    for s in sources:
        if isinstance(s, dict):
            normalized_sources.append(
                {
                    "documentId": s.get("documentId"),
                    "fileName": s.get("fileName"),
                    "excerpt": s.get("excerpt"),
                }
            )
    return normalized_sources


def _normalize_single_requirement(item: Any) -> dict[str, Any] | None:
    """Normalize a single requirement item."""
    if not isinstance(item, dict):
        return None

    text = (item.get("text") or "").strip()
    if not text:
        return None

    return {
        "id": item.get("id") or str(uuid.uuid4()),
        "category": _extract_category(item),
        "text": text,
        "ambiguity": _extract_ambiguity(item),
        "sources": _extract_sources(item),
    }


def _normalize_questions(state_data: dict[str, Any]) -> None:
    """Normalize clarification questions and handle linking."""
    req_list: list[dict[str, Any]] = state_data.get("requirements") or []
    req_ids_by_index: dict[int, str] = {
        idx: r["id"]
        for idx, r in enumerate(req_list)
        if isinstance(r, dict) and isinstance(r.get("id"), str)
    }

    clarification_questions: list[dict[str, Any]] = []
    raw_questions = state_data.get("clarificationQuestions", []) or []

    for q in raw_questions:
        normalized = _normalize_single_question(q, req_ids_by_index)
        if normalized:
            clarification_questions.append(normalized)

    # Fallback to openQuestions list (legacy field)
    if not clarification_questions:
        clarification_questions = _get_clarification_questions_from_legacy(state_data)

    if not state_data.get("clarificationQuestions"):
        state_data["clarificationQuestions"] = clarification_questions
    else:
        _ensure_ids_on_existing_questions(state_data)


def _normalize_single_question(
    q: Any, req_ids_by_index: dict[int, str]
) -> dict[str, Any] | None:
    """Normalize a single clarification question."""
    if not isinstance(q, dict):
        return None

    question_text = (q.get("question") or "").strip()
    if not question_text:
        return None

    related_indexes = q.get("relatedRequirementIndexes")
    related_requirement_ids: list[str] = []
    if isinstance(related_indexes, list):
        for idx in related_indexes:
            if isinstance(idx, int) and idx in req_ids_by_index:
                related_requirement_ids.append(req_ids_by_index[idx])

    return {
        "id": q.get("id") or str(uuid.uuid4()),
        "question": question_text,
        "status": q.get("status") or "open",
        "priority": q.get("priority"),
        "relatedRequirementIds": related_requirement_ids,
    }


def _get_clarification_questions_from_legacy(
    state_data: dict[str, Any],
) -> list[dict[str, Any]]:
    """Fallback to openQuestions list (legacy field)."""
    clarification_questions: list[dict[str, Any]] = []
    for oq in state_data.get("openQuestions", []) or []:
        if isinstance(oq, str) and oq.strip():
            clarification_questions.append(
                {
                    "id": str(uuid.uuid4()),
                    "question": oq.strip(),
                    "status": "open",
                    "relatedRequirementIds": [],
                }
            )
    return clarification_questions


def _ensure_ids_on_existing_questions(state_data: dict[str, Any]) -> None:
    """Ensure ids exist for any existing items."""
    existing_qs = state_data.get("clarificationQuestions", [])
    if isinstance(existing_qs, list):
        for qq in existing_qs:
            if isinstance(qq, dict) and not qq.get("id"):
                qq["id"] = str(uuid.uuid4())
