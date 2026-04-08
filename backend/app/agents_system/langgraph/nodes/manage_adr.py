"""Dedicated stage worker for explicit ADR drafting runtime execution."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents_system.services.project_context import read_project_state
from app.features.agent.application.adr_management_worker import (
    ADRManagementWorker,
    create_adr_management_worker,
)

from ..state import GraphState

logger = logging.getLogger(__name__)

StreamEventCallback = Callable[[str, dict[str, Any]], Awaitable[None] | None]


async def execute_manage_adr_stage_worker_node(
    state: GraphState,
    db: AsyncSession,
    *,
    worker: ADRManagementWorker | Any | None = None,
) -> dict[str, Any]:
    """Run the manage_adr stage through the explicit ADR worker runtime."""
    if state.get("next_stage") != "manage_adr":
        return {}

    project_id = state["project_id"]
    management_worker = worker or create_adr_management_worker()

    try:
        change_set = await management_worker.draft_and_record_pending_change(
            project_id=project_id,
            user_message=state.get("user_message", ""),
            project_state=state.get("current_project_state") or {},
            db=db,
            source_message_id=state.get("user_message_id"),
        )
        updated_project_state = await read_project_state(project_id, db)
        artifact_count = len(change_set.artifact_drafts)
        final_answer = (
            "ADR drafting complete. "
            f"I created pending change set `{change_set.id}` with {artifact_count} ADR draft(s). "
            "Review and approve it before it becomes canonical."
        )
        await _emit_stage_message(state.get("event_callback"), final_answer)
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
        await _emit_stage_message(state.get("event_callback"), final_answer)
        return {
            "agent_output": final_answer,
            "final_answer": final_answer,
            "intermediate_steps": [],
            "handled_by_stage_worker": True,
            "success": False,
            "error": str(exc),
        }
    except Exception as exc:  # noqa: BLE001
        logger.error("manage_adr stage worker failed: %s", exc, exc_info=True)
        final_answer = f"ERROR: ADR drafting failed: {exc!s}"
        await _emit_stage_message(state.get("event_callback"), final_answer)
        return {
            "agent_output": final_answer,
            "final_answer": final_answer,
            "intermediate_steps": [],
            "handled_by_stage_worker": True,
            "success": False,
            "error": f"ADR drafting failed: {exc!s}",
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
