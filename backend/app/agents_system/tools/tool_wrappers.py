import asyncio
import contextlib
import inspect
import json
import threading
from concurrent.futures import Future
from typing import Any


def make_single_input_wrapper(name: str, func: Any, async_func: Any | None = None):
    """Wrap a tool function to handle JSON string/dict/raw single-input payloads."""

    async def _async_runner(single_input):
        payload = _parse_tool_input(single_input)
        target_fn = async_func or func

        try:
            return await _call_function(target_fn, payload)
        except Exception:  # noqa: BLE001
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
    maybe = target_fn(payload)
    if inspect.isawaitable(maybe):
        return await maybe
    return maybe


def _run_async_in_new_thread(coro: Any) -> Any:
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
