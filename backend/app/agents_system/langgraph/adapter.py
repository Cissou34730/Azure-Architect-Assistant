"""
Adapter for LangGraph project chat execution.

Provides a simple interface matching the router's expectations.
"""

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..runner import get_agent_runner
from ..services.response_sanitizer import sanitize_agent_output
from .graph_factory import build_project_chat_graph
from .nodes.agent_native import run_stage_aware_agent
from .state import GraphState

logger = logging.getLogger(__name__)
_INTERMEDIATE_STEP_PARTS = 2


def _sse_event(event: str, payload: dict[str, Any]) -> str:
    data = json.dumps(payload, ensure_ascii=True)
    return f"event: {event}\ndata: {data}\n\n"


def _build_thread_config(thread_id: str | None) -> dict[str, Any] | None:
    """Build LangGraph config with thread_id for checkpointer."""
    if thread_id:
        return {"configurable": {"thread_id": thread_id}}
    return None


def _build_reasoning_step(step: object) -> dict[str, str] | None:
    """Normalize an intermediate agent step for SSE consumers."""
    if not isinstance(step, tuple) or len(step) != _INTERMEDIATE_STEP_PARTS:
        return None

    action, observation = step
    return {
        "action": action.tool if hasattr(action, "tool") else str(action),
        "action_input": action.tool_input if hasattr(action, "tool_input") else "",
        "observation": str(observation)[:500],
    }


async def execute_chat(user_message: str) -> dict[str, Any]:
    """Execute a non-project chat using the LangGraph-native tool loop.

    This supports the plain `/api/agent/chat` endpoint.

    Returns a dict compatible with AgentRunner.execute_query:
    - output
    - success
    - intermediate_steps
    - error
    """
    try:
        runner = await get_agent_runner()

        state: GraphState = {
            "user_message": user_message,
            "success": False,
            "retry_count": 0,
        }

        result = await run_stage_aware_agent(
            state,
            mcp_client=getattr(runner, "mcp_client", None),
            openai_settings=getattr(runner, "openai_settings", None),
        )
        output = sanitize_agent_output(str(result.get("agent_output", "")))

        return {
            "output": output,
            "success": bool(result.get("success", False)),
            "intermediate_steps": result.get("intermediate_steps", []),
            "error": result.get("error"),
        }
    except Exception as e:
        logger.error("LangGraph chat execution failed: %s", e, exc_info=True)
        return {
            "output": "",
            "success": False,
            "intermediate_steps": [],
            "error": f"LangGraph chat execution failed: {e!s}",
        }


async def execute_project_chat(
    project_id: str,
    user_message: str,
    db: AsyncSession,
    thread_id: str | None = None,
) -> dict[str, Any]:
    """Execute project-aware chat via LangGraph, compatible with router expectations.

    Returns a dict with:
    - output: final answer
    - success: bool
    - updated_project_state: dict or None
    - intermediate_steps: list
    - error: optional
    """
    try:
        response_message_id = str(uuid.uuid4())
        graph = build_project_chat_graph(
            db,
            response_message_id,
            enable_stage_routing=True,
            enable_multi_agent=False,
        )
        initial_state: GraphState = {
            "project_id": project_id,
            "user_message": user_message,
            "thread_id": thread_id,
            "success": False,
            "retry_count": 0,
        }
        config = _build_thread_config(thread_id)
        result = await graph.ainvoke(initial_state, config=config)
        output = str(result.get("final_answer", ""))
        if not output:
            output = sanitize_agent_output(str(result.get("agent_output", "")))
        return {
            "output": output,
            "success": bool(result.get("success", False)),
            "updated_project_state": result.get("updated_project_state"),
            "intermediate_steps": result.get("intermediate_steps", []),
            "error": result.get("error"),
        }
    except Exception as e:
        logger.error("LangGraph project chat execution failed: %s", e, exc_info=True)
        return {
            "output": "",
            "success": False,
            "updated_project_state": None,
            "intermediate_steps": [],
            "error": f"LangGraph project chat execution failed: {e!s}",
        }


async def execute_project_chat_stream(
    project_id: str,
    user_message: str,
    db: AsyncSession,
    thread_id: str | None = None,
) -> AsyncIterator[str]:
    queue: asyncio.Queue[str | None] = asyncio.Queue()

    async def _emit(event_type: str, payload: dict[str, Any]) -> None:
        await queue.put(_sse_event(event_type, payload))

    async def _run() -> None:
        try:
            response_message_id = str(uuid.uuid4())
            graph = build_project_chat_graph(
                db,
                response_message_id,
                enable_stage_routing=True,
                enable_multi_agent=False,
            )
            initial_state: GraphState = {
                "project_id": project_id,
                "user_message": user_message,
                "thread_id": thread_id,
                "success": False,
                "retry_count": 0,
                "event_callback": _emit,
            }
            config = _build_thread_config(thread_id)
            result_state = await graph.ainvoke(initial_state, config=config)
            final_answer = str(result_state.get("final_answer", ""))
            success = bool(result_state.get("success", False))
            updated_state = result_state.get("updated_project_state")
            reasoning_steps = []
            intermediate_steps = result_state.get("intermediate_steps", [])
            for step in intermediate_steps:
                reasoning_step = _build_reasoning_step(step)
                if reasoning_step is not None:
                    reasoning_steps.append(reasoning_step)
            fallback_output = sanitize_agent_output(str(result_state.get("agent_output", "")))
            await _emit(
                "final",
                {
                    "answer": final_answer if final_answer else fallback_output,
                    "success": success,
                    "project_state": updated_state,
                    "reasoning_steps": reasoning_steps,
                    "error": result_state.get("error"),
                },
            )
        except Exception as exc:
            logger.error("LangGraph streaming execution failed: %s", exc, exc_info=True)
            await _emit("error", {"error": f"Graph execution failed: {exc!s}"})
        finally:
            await queue.put(None)

    task = asyncio.create_task(_run())
    try:
        while True:
            item = await queue.get()
            if item is None:
                break
            yield item
    finally:
        await task
