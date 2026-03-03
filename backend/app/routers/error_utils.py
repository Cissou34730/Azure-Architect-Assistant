"""Shared error mapping helpers for API routers."""

from __future__ import annotations

import logging

from fastapi import HTTPException


def map_value_error(
    exc: ValueError,
    *,
    default_status: int = 400,
    not_found_hint: str | None = None,
) -> HTTPException:
    """Map ValueError to HTTPException using explicit router intent.

    Heuristic mapping from error text to 404 is opt-in only via ``not_found_hint``.
    """
    message = str(exc)
    status_code = (
        404
        if not_found_hint is not None and not_found_hint in message.lower()
        else default_status
    )
    return HTTPException(status_code=status_code, detail=message)


def internal_server_error(
    *,
    logger: logging.Logger,
    message: str,
    exc: Exception,
    detail_prefix: str,
) -> HTTPException:
    logger.error(message, exc_info=True)
    return HTTPException(status_code=500, detail=detail_prefix)
