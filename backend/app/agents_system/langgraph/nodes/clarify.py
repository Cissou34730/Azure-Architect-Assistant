"""Dedicated stage worker for clarify runtime execution."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from app.features.agent.application.clarification_planner_worker import (
    ClarificationPlannerWorker,
)
from app.features.agent.contracts.clarification_planner import (
    ClarificationPlanningResultContract,
)

from ..state import GraphState

logger = logging.getLogger(__name__)

StreamEventCallback = Callable[[str, dict[str, Any]], Awaitable[None] | None]


async def execute_clarification_planner_node(
    state: GraphState,
    *,
    worker: ClarificationPlannerWorker | None = None,
) -> dict[str, Any]:
    """Run the clarify stage through the clarification planning worker."""
    if state.get("next_stage") != "clarify":
        return {}

    planner_worker = worker or ClarificationPlannerWorker()
    try:
        plan = await planner_worker.plan_questions(
            user_message=str(state.get("user_message") or ""),
            current_state=_project_state_from_graph_state(state),
            mindmap_coverage=_mindmap_coverage_from_graph_state(state),
        )
        final_answer = _format_clarification_plan(plan)
        await _emit_stage_message(state.get("event_callback"), final_answer)
        return {
            "agent_output": final_answer,
            "final_answer": final_answer,
            "intermediate_steps": [],
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
        logger.error("clarify stage worker failed: %s", exc, exc_info=True)
        final_answer = f"ERROR: Clarification planning failed: {exc!s}"
        await _emit_stage_message(state.get("event_callback"), final_answer)
        return {
            "agent_output": final_answer,
            "final_answer": final_answer,
            "intermediate_steps": [],
            "handled_by_stage_worker": True,
            "success": False,
            "error": f"Clarification planning failed: {exc!s}",
        }


def _project_state_from_graph_state(state: GraphState) -> dict[str, Any]:
    project_state = state.get("current_project_state")
    if isinstance(project_state, dict):
        return project_state
    return {}


def _mindmap_coverage_from_graph_state(state: GraphState) -> dict[str, Any] | None:
    mindmap_coverage = state.get("mindmap_coverage")
    if isinstance(mindmap_coverage, dict):
        return mindmap_coverage
    return None


def _format_clarification_plan(plan: ClarificationPlanningResultContract) -> str:
    total_questions = sum(len(group.questions) for group in plan.question_groups)
    lines = [
        "Clarification planning complete. "
        f"I identified {total_questions} high-impact question(s) grouped by theme.",
        "",
    ]

    for group in plan.question_groups:
        lines.append(f"**{group.theme}**")
        for index, question in enumerate(group.questions, start=1):
            lines.append(f"{index}. [{question.architectural_impact}] {question.question}")
            lines.append(f"   Why it matters: {question.why_it_matters}")
        lines.append("")

    lines.append("Please answer the questions you can, and I will use them to refine the architecture.")
    return "\n".join(lines).strip()


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
