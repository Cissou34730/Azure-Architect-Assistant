"""Dedicated stage worker for extract_requirements runtime execution."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents_system.services.project_context import read_project_state
from app.features.projects.application.requirements_extraction_entry_service import (
    ProjectRequirementsExtractionEntryService,
    create_requirements_extraction_entry_service,
)

from ..state import GraphState

logger = logging.getLogger(__name__)

StreamEventCallback = Callable[[str, dict[str, Any]], Awaitable[None] | None]


async def execute_extract_requirements_node(
    state: GraphState,
    db: AsyncSession,
    *,
    entry_service: ProjectRequirementsExtractionEntryService | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the extract_requirements stage worker inside the project chat graph."""
    if state.get("next_stage") != "extract_requirements":
        return {}

    event_callback = (
        ((config or {}).get("configurable") or {}).get("event_callback")
        or state.get("event_callback")
    )

    project_id = state["project_id"]
    service = entry_service or create_requirements_extraction_entry_service()
    source_message_id = state.get("user_message_id")

    try:
        change_set = await service.extract_pending_requirements(
            project_id=project_id,
            db=db,
            source_message_id=source_message_id,
        )
        updated_project_state = await read_project_state(project_id, db)
        requirements_payload = change_set.proposed_patch.get("requirements", [])
        requirement_count = len(requirements_payload) if isinstance(requirements_payload, list) else 0
        final_answer = (
            "Requirements extraction complete. "
            f"I created pending change set `{change_set.id}` with {requirement_count} requirement draft(s). "
            "Review and approve it before it becomes canonical."
        )
        await _emit_stage_message(event_callback, final_answer)
        return {
            "agent_output": final_answer,
            "final_answer": final_answer,
            "intermediate_steps": [],
            "updated_project_state": updated_project_state or state.get("current_project_state"),
            "handled_by_stage_worker": True,
            "success": True,
        }
    except ValueError as exc:
        final_answer = f"ERROR: {exc!s}"
        await _emit_stage_message(event_callback, final_answer)
        return {
            "agent_output": final_answer,
            "final_answer": final_answer,
            "intermediate_steps": [],
            "handled_by_stage_worker": True,
            "success": False,
            "error": str(exc),
        }
    except Exception as exc:
        logger.error("extract_requirements stage worker failed: %s", exc, exc_info=True)
        final_answer = f"ERROR: Requirements extraction failed: {exc!s}"
        await _emit_stage_message(event_callback, final_answer)
        return {
            "agent_output": final_answer,
            "final_answer": final_answer,
            "intermediate_steps": [],
            "handled_by_stage_worker": True,
            "success": False,
            "error": f"Requirements extraction failed: {exc!s}",
        }


async def _emit_stage_message(
    callback: StreamEventCallback | Any,
    text: str,
) -> None:
    if not callable(callback):
        return
    await _emit(callback, "message_start", {"role": "assistant"})
    await _emit(callback, "token", {"text": text})


async def _emit(
    callback: StreamEventCallback,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    result = callback(event_type, payload)
    if asyncio.iscoroutine(result):
        await result
