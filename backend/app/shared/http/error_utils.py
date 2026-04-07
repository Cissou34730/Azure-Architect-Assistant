"""Shared error mapping helpers for API routers."""

from __future__ import annotations

import logging

from fastapi import HTTPException


def map_value_error(
    exc: ValueError,
    *,
    default_status: int = 400,
) -> HTTPException:
    """Map ValueError to HTTPException using explicit router intent."""
    message = str(exc)
    return HTTPException(status_code=default_status, detail=message)


def internal_server_error(
    *,
    logger: logging.Logger,
    message: str,
    exc: Exception,
    detail_prefix: str,
) -> HTTPException:
    logger.error(message, exc_info=True)
    return HTTPException(status_code=500, detail=detail_prefix)
