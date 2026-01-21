import asyncio
import contextlib
import inspect
import json
import logging
import threading
from concurrent.futures import Future
from typing import Any

logger = logging.getLogger(__name__)


def make_single_input_wrapper(name: str, func: Any, async_func: Any | None = None):
    """
    Wraps a tool function to handle various input formats (JSON string, dict, or raw value)
    and ensure it can be called correctly by LangChain agents.
    Returns a (sync_wrapper, async_wrapper) tuple.
    """

    async def _async_runner(single_input):
        payload = _parse_tool_input(single_input)
        target_fn = async_func or func

        try:
            return await _call_function(target_fn, payload)
        except Exception:  # noqa: BLE001
            # Fallback for complex argument mismatches
            return await _call_function_fallback(target_fn, payload)

    def _sync_wrapper(single_input):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return _run_async_in_new_thread(_async_runner(single_input))
            return asyncio.run(_async_runner(single_input))
        except RuntimeError:
            return asyncio.run(_async_runner(single_input))

    _async_runner.__name__ = name
    _sync_wrapper.__name__ = name

    return _sync_wrapper, _async_runner


def _parse_tool_input(single_input: Any) -> Any:
    """Normalize input into a payload (dict or string)."""
    if isinstance(single_input, str):
        try:
            clean_input = single_input.strip()
            if clean_input.startswith('"') and clean_input.endswith('"'):
                with contextlib.suppress(json.JSONDecodeError, TypeError):
                    clean_input = json.loads(clean_input)
            return json.loads(clean_input)
        except (json.JSONDecodeError, TypeError, ValueError):
            return {"query": single_input}
    if isinstance(single_input, dict):
        return single_input
    return {"value": single_input}


async def _call_function(target_fn: Any, payload: Any) -> Any:
    """Execute target function with appropriate argument passing."""
    try:
        maybe = target_fn(payload)
        if inspect.isawaitable(maybe):
            return await maybe
        return maybe
    except TypeError:
        maybe = target_fn(**payload) if isinstance(payload, dict) else target_fn(payload)
        if inspect.isawaitable(maybe):
            return await maybe
        return maybe


async def _call_function_fallback(target_fn: Any, payload: Any) -> Any:
    """Last resort fallback for function calls."""
    maybe = target_fn(payload)
    if inspect.isawaitable(maybe):
        return await maybe
    return maybe


def _run_async_in_new_thread(coro: Any) -> Any:
    """Run an async coroutine in a new thread with its own event loop."""

    def _thread_worker(fut, coro):
        try:
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            result = new_loop.run_until_complete(coro)
            fut.set_result(result)
        except Exception as e:  # noqa: BLE001
            fut.set_exception(e)
        finally:
            new_loop.close()

    fut = Future()
    t = threading.Thread(target=_thread_worker, args=(fut, coro))
    t.start()
    return fut.result()


def normalize_agent_result(raw: Any) -> dict[str, Any]:
    """
    Normalizes different agent return shapes to a consistent dict format.
    Ensures 'output' and 'intermediate_steps' keys are present.
    """
    if isinstance(raw, dict):
        return {
            "output": raw.get("output") or raw.get("result") or str(raw),
            "intermediate_steps": raw.get("intermediate_steps", [])
        }
    if isinstance(raw, str):
        return {"output": raw, "intermediate_steps": []}
    return {"output": str(raw), "intermediate_steps": []}

