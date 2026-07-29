"""Shared transient-fault retry helper for LLM provider calls.

The OpenAI SDK clients in this codebase are created with ``max_retries=0``
so that SDK-level silent retries never mask timeout errors.  The trade-off is
that transient faults (rate limits, gateway 5xx, connection drops, timeouts)
previously propagated straight to the caller with no retry at all.

This module provides a single, explicit retry policy that providers can apply
around a whole dispatch (including their internal compatibility fallbacks).
It mirrors the exponential-backoff-with-jitter strategy already used by the
Microsoft Learn MCP client so behaviour is consistent across the codebase.
"""

from __future__ import annotations

import asyncio
import logging
import secrets
from collections.abc import Awaitable, Callable
from typing import TypeVar

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")

#: Exceptions that are always considered transient (worth retrying).
_TRANSIENT_EXCEPTION_TYPES: tuple[type[BaseException], ...] = (
    RateLimitError,
    APITimeoutError,
    APIConnectionError,
    InternalServerError,
)

#: HTTP status codes treated as transient when surfaced via APIStatusError.
_TRANSIENT_STATUS_CODES: frozenset[int] = frozenset({408, 409, 425, 429, 500, 502, 503, 504})


def is_transient_llm_error(error: BaseException) -> bool:
    """Return True when *error* looks like a transient infrastructure fault.

    Transient faults are worth retrying: rate limiting, timeouts, connection
    errors and gateway/server 5xx responses.  Client errors such as 400/401/
    403/404 are deterministic and are never retried here.
    """
    if isinstance(error, _TRANSIENT_EXCEPTION_TYPES):
        return True
    if isinstance(error, APIStatusError):
        status_code = getattr(error, "status_code", None)
        return isinstance(status_code, int) and status_code in _TRANSIENT_STATUS_CODES
    return False


async def call_with_transient_retry(
    fn: Callable[[], Awaitable[T]],
    *,
    max_attempts: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 8.0,
    operation: str = "LLM call",
) -> T:
    """Await ``fn()`` retrying transient failures with exponential backoff + jitter.

    Args:
        fn: Zero-arg async callable to invoke.
        max_attempts: Total attempts (1 = no retry).
        base_delay: Initial backoff in seconds; doubles each attempt.
        max_delay: Backoff cap in seconds.
        operation: Human-readable label used in log messages.

    Raises:
        The last exception raised by ``fn`` when attempts are exhausted, or
        immediately when the error is not transient.
    """
    attempts = max(int(max_attempts), 1)
    last_error: BaseException | None = None

    for attempt in range(1, attempts + 1):
        try:
            return await fn()
        except Exception as error:  # noqa: BLE001 - classified below
            last_error = error
            if not is_transient_llm_error(error):
                raise
            if attempt >= attempts:
                break
            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            jitter = secrets.randbelow(250) / 1000.0
            sleep_for = min(delay + jitter, max_delay)
            logger.warning(
                "%s failed with transient error (attempt %d/%d): %s — retrying in %.2fs",
                operation,
                attempt,
                attempts,
                error,
                sleep_for,
            )
            await asyncio.sleep(sleep_for)

    assert last_error is not None  # for type-checkers; loop guarantees this
    logger.error("%s failed after %d attempts: %s", operation, attempts, last_error)
    raise last_error
