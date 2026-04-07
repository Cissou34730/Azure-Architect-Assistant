"""AAA artifacts management tool.

Provides a single tool for creating, updating, and removing
requirements, assumptions, and clarification questions in
ProjectState via the existing AAA_STATE_UPDATE pipeline.

This tool does NOT call external services.  The agent builds the
artifact payload and this tool formats it as an AAA_STATE_UPDATE
JSON block that the state-update parser picks up.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

ArtifactType = Literal["requirement", "assumption", "clarification_question"]
Action = Literal["add", "update", "remove", "replace_all"]

_STATE_KEY_MAP: dict[str, str] = {
    "requirement": "requirements",
    "assumption": "assumptions",
    "clarification_question": "clarificationQuestions",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


# ── Input schema ──────────────────────────────────────────────────────


class AAAManageArtifactsToolInput(BaseModel):
    """Raw tool payload."""

    payload: str | dict[str, Any] = Field(
        description=(
            "A JSON object (or JSON string) with keys: "
            "artifact_type ('requirement'|'assumption'|'clarification_question'), "
            "action ('add'|'update'|'remove'|'replace_all'), "
            "items (list of artifact dicts)."
        ),
    )


# ── Builders ──────────────────────────────────────────────────────────


def _build_requirement(item: dict[str, Any], action: str) -> dict[str, Any]:
    if action == "add":
        return {
            "id": item.get("id") or _new_id(),
            "text": item["text"].strip(),
            "category": item.get("category", "functional"),
            "ambiguity": item.get("ambiguity", {"isAmbiguous": False, "notes": ""}),
            "sources": item.get("sources", []),
        }
    if action == "update":
        out: dict[str, Any] = {"id": item["id"]}
        if "text" in item:
            out["text"] = item["text"].strip()
        if "category" in item:
            out["category"] = item["category"]
        if "ambiguity" in item:
            out["ambiguity"] = item["ambiguity"]
        if "sources" in item:
            out["sources"] = item["sources"]
        return out
    # remove
    return {"id": item["id"], "_remove": True}


def _build_assumption(item: dict[str, Any], action: str) -> dict[str, Any]:
    if action == "add":
        return {
            "id": item.get("id") or _new_id(),
            "text": item["text"].strip(),
            "status": item.get("status", "open"),
            "relatedRequirementIds": item.get("relatedRequirementIds", []),
        }
    if action == "update":
        out: dict[str, Any] = {"id": item["id"]}
        if "text" in item:
            out["text"] = item["text"].strip()
        if "status" in item:
            out["status"] = item["status"]
        if "relatedRequirementIds" in item:
            out["relatedRequirementIds"] = item["relatedRequirementIds"]
        return out
    return {"id": item["id"], "_remove": True}


def _build_question(item: dict[str, Any], action: str) -> dict[str, Any]:
    if action in ("add", "replace_all"):
        return {
            "id": item.get("id") or _new_id(),
            "question": item["question"].strip(),
            "status": item.get("status", "open"),
            "priority": item.get("priority"),
            "relatedRequirementIds": item.get("relatedRequirementIds", []),
        }
    if action == "update":
        out: dict[str, Any] = {"id": item["id"]}
        if "question" in item:
            out["question"] = item["question"].strip()
        if "status" in item:
            out["status"] = item["status"]
        if "priority" in item:
            out["priority"] = item["priority"]
        if "relatedRequirementIds" in item:
            out["relatedRequirementIds"] = item["relatedRequirementIds"]
        return out
    return {"id": item["id"], "_remove": True}


_BUILDERS: dict[str, Any] = {
    "requirement": _build_requirement,
    "assumption": _build_assumption,
    "clarification_question": _build_question,
}


# ── Tool ──────────────────────────────────────────────────────────────


class AAAManageArtifactsTool(BaseTool):
    """Tool to create, update, remove, or replace requirements, assumptions, and clarification questions."""

    name: str = "aaa_manage_artifacts"
    description: str = (
        "Create, update, remove, or fully replace requirements, assumptions, and clarification "
        "questions in ProjectState.  Returns an AAA_STATE_UPDATE JSON block.\n"
        "\n"
        "Input payload keys:\n"
        "  artifact_type: 'requirement' | 'assumption' | 'clarification_question'\n"
        "  action: 'add' | 'update' | 'remove' | 'replace_all'\n"
        "  items: list of artifact dicts\n"
        "\n"
        "For 'add': items need 'text' (requirements/assumptions) or 'question' (clarification_question). "
        "Optional fields: category, priority, relatedRequirementIds, status.\n"
        "For 'update': items MUST include 'id' plus the fields to change.\n"
        "For 'remove': items MUST include 'id'.\n"
        "For 'replace_all': replaces the entire list (use when regenerating all questions/requirements)."
    )

    args_schema: type[BaseModel] = AAAManageArtifactsToolInput

    def _run(
        self,
        payload: str | dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            raw = self._parse_payload(payload, **kwargs)
            artifact_type = raw.get("artifact_type", "")
            action = raw.get("action", "")
            items = raw.get("items", [])

            if artifact_type not in _STATE_KEY_MAP:
                raise ValueError(
                    f"Invalid artifact_type '{artifact_type}'. "
                    f"Must be one of: {', '.join(_STATE_KEY_MAP)}"
                )
            if action not in ("add", "update", "remove", "replace_all"):
                raise ValueError(
                    f"Invalid action '{action}'. Must be one of: add, update, remove, replace_all"
                )
            if not items:
                raise ValueError("items list must not be empty.")

            if action in ("update", "remove"):
                for item in items:
                    if not item.get("id"):
                        raise ValueError(
                            f"All items must have an 'id' for action='{action}'."
                        )

            builder = _BUILDERS[artifact_type]
            built = [builder(item, action) for item in items]

            state_key = _STATE_KEY_MAP[artifact_type]
            updates: dict[str, Any] = {state_key: built}

            if action == "replace_all":
                updates[f"_replace_{state_key}"] = True

            payload_str = json.dumps(updates, ensure_ascii=False, indent=2)
            count = len(built)
            label = artifact_type.replace("_", " ")

            return (
                f"{action.capitalize()}d {count} {label}(s) at {_now_iso()}.\n"
                "\n"
                "AAA_STATE_UPDATE\n"
                "```json\n"
                f"{payload_str}\n"
                "```"
            )
        except Exception as exc:  # noqa: BLE001
            return f"ERROR: {exc!s}"

    def _parse_payload(
        self, payload: str | dict[str, Any] | None, **kwargs: Any
    ) -> dict[str, Any]:
        if payload is None:
            payload = kwargs.get("payload") or kwargs.get("tool_input")
            if payload is None:
                raise ValueError("Missing payload for artifact management")

        if isinstance(payload, str):
            try:
                return json.loads(payload.strip())
            except json.JSONDecodeError as exc:
                raise ValueError("Invalid JSON payload.") from exc
        return payload if isinstance(payload, dict) else {}

    async def _arun(self, **kwargs: Any) -> str:
        return self._run(**kwargs)
