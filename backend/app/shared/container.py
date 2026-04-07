"""Shared dependency helpers."""

from app.shared.config.app_settings import AppSettings, get_app_settings


def get_app_settings_dependency() -> AppSettings:
    return get_app_settings()
