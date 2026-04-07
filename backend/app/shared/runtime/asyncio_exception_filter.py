"""Asyncio exception filtering helpers."""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Callable, Mapping
from typing import Any

logger = logging.getLogger(__name__)

_WINDOWS_CONNECTION_RESET_WINERROR = 10054
_PROACTOR_CALLBACK_NAME = "_ProactorBasePipeTransport._call_connection_lost"
_INSTALL_MARKER = "_aaa_asyncio_exception_filter_installed"

ExceptionHandler = Callable[[asyncio.AbstractEventLoop, dict[str, Any]], None]


def is_benign_windows_pipe_close_error(
    context: Mapping[str, Any],
    *,
    platform: str | None = None,
) -> bool:
    """Return True for the known benign Windows Proactor pipe shutdown error."""
    effective_platform = os.name if platform is None else platform
    if effective_platform != "nt":
        return False

    exception = context.get("exception")
    if not isinstance(exception, ConnectionResetError):
        return False
    if getattr(exception, "winerror", None) != _WINDOWS_CONNECTION_RESET_WINERROR:
        return False

    message = str(context.get("message") or "")
    handle_repr = ""
    handle = context.get("handle")
    if handle is not None:
        handle_repr = repr(handle)

    return _PROACTOR_CALLBACK_NAME in message or _PROACTOR_CALLBACK_NAME in handle_repr


def build_asyncio_exception_handler(
    previous_handler: ExceptionHandler | None,
    *,
    platform: str | None = None,
) -> ExceptionHandler:
    """Build an exception handler that suppresses only the benign Windows pipe error."""

    def _handler(loop: asyncio.AbstractEventLoop, context: dict[str, Any]) -> None:
        if is_benign_windows_pipe_close_error(context, platform=platform):
            logger.debug(
                "Suppressed benign Windows asyncio pipe shutdown ConnectionResetError",
                exc_info=context.get("exception"),
            )
            return

        if previous_handler is not None:
            previous_handler(loop, context)
            return

        loop.default_exception_handler(context)

    return _handler


def install_asyncio_exception_filter(
    *,
    loop: asyncio.AbstractEventLoop | None = None,
    platform: str | None = None,
) -> None:
    """Install the Windows-specific asyncio exception filter on the target loop."""
    target_loop = loop or asyncio.get_running_loop()
    if getattr(target_loop, _INSTALL_MARKER, False):
        return

    previous_handler = target_loop.get_exception_handler()
    target_loop.set_exception_handler(
        build_asyncio_exception_handler(previous_handler, platform=platform)
    )
    setattr(target_loop, _INSTALL_MARKER, True)
