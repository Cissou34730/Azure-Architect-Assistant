"""Structured logging with correlation IDs for ingestion."""

from __future__ import annotations

import logging
import threading
from typing import Any

# Thread-local storage for correlation context
_context = threading.local()


class CorrelationFilter(logging.Filter):
    """Inject correlation IDs into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation fields to log record."""
        record.job_id = getattr(_context, 'job_id', None) or '-'
        record.kb_id = getattr(_context, 'kb_id', None) or '-'
        record.correlation_id = getattr(_context, 'correlation_id', None) or '-'
        return True


def set_correlation_context(
    job_id: str | None = None,
    kb_id: str | None = None,
    correlation_id: str | None = None,
) -> None:
    """Set correlation context for current thread."""
    if job_id is not None:
        _context.job_id = job_id
    if kb_id is not None:
        _context.kb_id = kb_id
    if correlation_id is not None:
        _context.correlation_id = correlation_id


def clear_correlation_context() -> None:
    """Clear correlation context for current thread."""
    _context.job_id = None
    _context.kb_id = None
    _context.correlation_id = None


def get_correlation_context() -> dict[str, str | None]:
    """Get current correlation context."""
    return {
        'job_id': getattr(_context, 'job_id', None),
        'kb_id': getattr(_context, 'kb_id', None),
        'correlation_id': getattr(_context, 'correlation_id', None),
    }


def configure_ingestion_logging(log_level: str = 'INFO') -> None:
    """Configure logging with correlation support."""
    logger = logging.getLogger('app.ingestion')
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Add correlation filter
    correlation_filter = CorrelationFilter()
    for handler in logger.handlers:
        handler.addFilter(correlation_filter)

    # If no handlers, add console handler with correlation format
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - [Job=%(job_id)s|KB=%(kb_id)s] - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        handler.addFilter(correlation_filter)
        logger.addHandler(handler)


class CorrelatedLogger:
    """Logger wrapper that automatically includes correlation context."""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def _log(self, level: int, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log with correlation context."""
        ctx = get_correlation_context()
        extra = kwargs.get('extra', {})
        extra.update(ctx)
        kwargs['extra'] = extra
        self.logger.log(level, msg, *args, **kwargs)

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._log(logging.DEBUG, msg, *args, **kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._log(logging.INFO, msg, *args, **kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._log(logging.WARNING, msg, *args, **kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._log(logging.ERROR, msg, *args, **kwargs)

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._log(logging.CRITICAL, msg, *args, **kwargs)


def get_correlated_logger(name: str) -> CorrelatedLogger:
    """Get a logger with automatic correlation context."""
    return CorrelatedLogger(logging.getLogger(name))
