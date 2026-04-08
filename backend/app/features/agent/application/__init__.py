"""Agent application package with lazy exports to avoid import cycles."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORT_MAP = {
    "ADRManagementWorker": ("adr_management_worker", "ADRManagementWorker"),
    "ADRLifecycleError": ("adr_lifecycle_service", "ADRLifecycleError"),
    "ADRLifecycleService": ("adr_lifecycle_service", "ADRLifecycleService"),
    "AgentApiService": ("agent_api_service", "AgentApiService"),
    "ClarificationResolutionWorker": (
        "clarification_resolution_worker",
        "ClarificationResolutionWorker",
    ),
    "RequirementsExtractionService": ("requirements_extraction_service", "RequirementsExtractionService"),
    "RequirementsExtractionWorker": ("requirements_extraction_worker", "RequirementsExtractionWorker"),
    "create_adr_management_worker": ("adr_management_worker", "create_adr_management_worker"),
    "create_clarification_resolution_worker": (
        "clarification_resolution_worker",
        "create_clarification_resolution_worker",
    ),
    "get_agent_api_service": ("agent_api_service", "get_agent_api_service"),
}


def __getattr__(name: str) -> Any:
    if name not in _EXPORT_MAP:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
    module_name, attribute_name = _EXPORT_MAP[name]
    module = import_module(f"{__name__}.{module_name}")
    return getattr(module, attribute_name)


__all__ = sorted(_EXPORT_MAP)
