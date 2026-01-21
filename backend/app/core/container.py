"""
Simple dependency helpers shared across routers and services.
"""

from app.core.app_settings import AppSettings, get_app_settings


def get_settings() -> AppSettings:
    """Expose AppSettings for FastAPI dependency injection."""
    return get_app_settings()

