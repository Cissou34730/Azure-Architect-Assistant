"""Graph node modules exposed through lazy package attributes."""

from __future__ import annotations

from importlib import import_module
from types import ModuleType

_EXPORTED_MODULES = {"clarify", "extract_requirements", "manage_adr", "validate"}


def __getattr__(name: str) -> ModuleType:
    if name in _EXPORTED_MODULES:
        return import_module(f"{__name__}.{name}")
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = sorted(_EXPORTED_MODULES)
