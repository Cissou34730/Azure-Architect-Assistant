"""
Logging configuration helpers for the FastAPI backend.
"""

import logging
from typing import Iterable


DEFAULT_LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging(level: str = "INFO", noisy_loggers: Iterable[str] = None) -> None:
    """
    Configure root and framework loggers with a consistent format.

    Args:
        level: Log level name (e.g., INFO, DEBUG).
        noisy_loggers: Optional iterable of logger names to downgrade to WARNING.
    """
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=DEFAULT_LOG_FORMAT,
        datefmt=DEFAULT_DATE_FORMAT,
        force=True,
    )

    # Set uvicorn loggers to the chosen level (keep access logs separate).
    for logger_name in ["uvicorn", "uvicorn.error"]:
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    access_logger = logging.getLogger("uvicorn.access")
    access_logger.setLevel(logging.INFO)

    # Quiet down noisy HTTP clients by default.
    for noisy in noisy_loggers or ["httpx", "openai", "urllib3", "httpcore"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)
