"""Dedicated stage worker for export runtime execution."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from app.features.agent.infrastructure.tools.aaa_export_tool import AAAExportTool

from ..state import GraphState

StreamEventCallback = Callable[[str, dict[str, Any]], Awaitable[None] | None]


async def execute_export_stage_worker_node(
    state: GraphState,
    *,
    export_tool: AAAExportTool | Any | None = None,
) -> dict[str, Any]:
    """Run export turns through the dedicated deterministic export tool."""
    if state.get("next_stage") != "export":
        return {}

    project_id = str(state.get("project_id") or "aaa")
    tool = export_tool or AAAExportTool()
    agent_output = tool._run(
        payload={
            "exportFormat": "json",
            "state": state.get("current_project_state") or {},
            "pretty": True,
            "fileName": f"{project_id}-aaa-export.json",
        }
    )
    success = not str(agent_output).strip().startswith("ERROR:")
    error = None if success else str(agent_output).removeprefix("ERROR:").strip() or str(agent_output)
    await _emit_stage_message(state.get("event_callback"), agent_output)
    return {
        "agent_output": agent_output,
        "final_answer": agent_output,
        "intermediate_steps": [],
        "handled_by_stage_worker": True,
        "success": success,
        "error": error,
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
