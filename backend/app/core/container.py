"""
Simple dependency helpers shared across routers and services.
"""

from app.core.config import get_app_settings, AppSettings


def get_settings() -> AppSettings:
    """Expose AppSettings for FastAPI dependency injection."""
    return get_app_settings()
