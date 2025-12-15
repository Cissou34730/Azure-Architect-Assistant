"""[ARCHIVED] Safe asyncio executor utilities (no longer used).

This module has been archived to `archive/ingestion_legacy/executor.py`.
It remains here only as a stub to avoid import errors until all references
are cleaned up. Do not use in new code.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any, Callable, Coroutine, Optional, TypeVar

from config import get_settings

logger = logging.getLogger(__name__)

T = TypeVar('T')

# Thread-local storage for event loop
_thread_locals = threading.local()


def get_or_create_event_loop() -> asyncio.AbstractEventLoop:
    """Get or create event loop for current thread."""
    try:
        loop = asyncio.get_running_loop()
        return loop
    except RuntimeError:
        # No running loop, create one
        if not hasattr(_thread_locals, 'loop') or _thread_locals.loop is None:
            _thread_locals.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(_thread_locals.loop)
        return _thread_locals.loop


def safe_run(coro: Coroutine[Any, Any, T]) -> T:
    """
    Safely run a coroutine, avoiding nested event loop errors.
    
    If called from within an existing event loop, schedules the coroutine
    as a task. Otherwise, runs it with asyncio.run().
    """
    try:
        loop = asyncio.get_running_loop()
        # Already in a loop - cannot use asyncio.run()
        logger.warning("safe_run called from within event loop - creating task")
        task = loop.create_task(coro)
        return loop.run_until_complete(task)
    except RuntimeError:
        # No running loop - safe to use asyncio.run()
        return asyncio.run(coro)


def run_in_thread_loop(coro: Coroutine[Any, Any, T]) -> T:
    """
    Run coroutine in thread-local event loop.
    
    Useful for worker threads that need to run async code repeatedly
    without creating new event loops each time.
    """
    loop = get_or_create_event_loop()
    if loop.is_running():
        # Use run_coroutine_threadsafe for running loops
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result()
    else:
        return loop.run_until_complete(coro)


async def run_sync_in_executor(
    func: Callable[..., T],
    *args: Any,
    executor: Optional[Any] = None,
    **kwargs: Any
) -> T:
    """
    Run synchronous function in executor to avoid blocking event loop.
    
    Args:
        func: Synchronous callable
        *args: Positional arguments
        executor: Optional executor (defaults to ThreadPoolExecutor)
        **kwargs: Keyword arguments
    """
    loop = asyncio.get_running_loop()
    if kwargs:
        # Wrap with lambda to pass kwargs
        return await loop.run_in_executor(executor, lambda: func(*args, **kwargs))
    else:
        return await loop.run_in_executor(executor, func, *args)


class AsyncioExecutor:
    """Stub class. Use archived version under `archive/ingestion_legacy/executor.py`."""

    def __init__(self):
        raise RuntimeError("AsyncioExecutor is archived. Import from archive if needed.")
