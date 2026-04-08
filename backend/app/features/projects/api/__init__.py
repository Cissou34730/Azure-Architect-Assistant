"""Projects API package."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from fastapi import APIRouter

__all__ = [
    "changes_router",
    "document_router",
    "get_chat_service_dep",
    "get_document_content_service_dep",
    "get_document_service_dep",
    "get_pending_changes_service_dep",
    "get_project_analysis_service_dep",
    "get_project_service_dep",
    "get_state_edit_service_dep",
    "get_workspace_composer_dep",
    "project_management_router",
    "project_router",
    "state_router",
    "workspace_router",
]


def __getattr__(name: str) -> Any:
    if name in {
        "changes_router",
        "document_router",
        "project_router",
        "state_router",
        "workspace_router",
    }:
        module = import_module(f"{__name__}.{name}")
        globals()[name] = module
        return module

    if name in {
        "get_chat_service_dep",
        "get_document_content_service_dep",
        "get_document_service_dep",
        "get_pending_changes_service_dep",
        "get_project_analysis_service_dep",
        "get_project_service_dep",
        "get_requirements_extraction_entry_service_dep",
        "get_state_edit_service_dep",
        "get_workspace_composer_dep",
    }:
        deps_module = import_module(f"{__name__}._deps")
        value = getattr(deps_module, name)
        globals()[name] = value
        return value

    if name == "project_management_router":
        router = APIRouter()
        router.include_router(__getattr__("project_router").router)
        router.include_router(__getattr__("document_router").router)
        router.include_router(__getattr__("changes_router").router)
        router.include_router(__getattr__("state_router").router)
        router.include_router(__getattr__("workspace_router").router)
        globals()[name] = router
        return router

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
