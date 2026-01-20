import asyncio
import inspect
import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def make_single_input_wrapper(name: str, func: Any, async_func: Optional[Any] = None):
    """
    Wraps a tool function to handle various input formats (JSON string, dict, or raw value)
    and ensure it can be called correctly by LangChain agents.
    Returns a (sync_wrapper, async_wrapper) tuple.
    """
    async def _async_runner(single_input):
        if isinstance(single_input, str):
            try:
                # Handle cases where LLM sends double-encoded JSON or JSON with extra quotes
                clean_input = single_input.strip()
                if clean_input.startswith('"') and clean_input.endswith('"'):
                    try:
                        clean_input = json.loads(clean_input)
                    except:
                        pass
                payload = json.loads(clean_input)
            except Exception:
                payload = {"query": single_input}
        elif isinstance(single_input, dict):
            payload = single_input
        else:
            payload = {"value": single_input}

        # Prefer async_func if provided, otherwise use func
        target_fn = async_func or func

        try:
            maybe = target_fn(payload)
            if inspect.isawaitable(maybe):
                return await maybe
            return maybe
        except TypeError:
            try:
                if isinstance(payload, dict):
                    maybe = target_fn(**payload)
                else:
                    maybe = target_fn(payload)
                
                if inspect.isawaitable(maybe):
                    return await maybe
                return maybe
            except Exception:
                maybe = target_fn(payload)
                if inspect.isawaitable(maybe):
                    return await maybe
                return maybe

    def _sync_wrapper(single_input):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Use a separate thread to run the async tool if we're already in a loop
                import threading
                from concurrent.futures import Future

                def _thread_worker(fut, coro):
                    try:
                        # Create a new loop for the thread
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        result = new_loop.run_until_complete(coro)
                        fut.set_result(result)
                    except Exception as e:
                        fut.set_exception(e)
                    finally:
                        new_loop.close()

                fut = Future()
                t = threading.Thread(target=_thread_worker, args=(fut, _async_runner(single_input)))
                t.start()
                return fut.result()
            else:
                return asyncio.run(_async_runner(single_input))
        except RuntimeError:
            return asyncio.run(_async_runner(single_input))

    _async_runner.__name__ = name
    _sync_wrapper.__name__ = name
    
    return _sync_wrapper, _async_runner


def normalize_agent_result(raw: Any) -> Dict[str, Any]:
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
