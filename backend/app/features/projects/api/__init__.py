"""Projects API package."""

from fastapi import APIRouter

from . import document_router, project_router, state_router, workspace_router
from ._deps import (
    get_chat_service_dep,
    get_document_content_service_dep,
    get_document_service_dep,
    get_project_analysis_service_dep,
    get_project_service_dep,
    get_state_edit_service_dep,
    get_workspace_composer_dep,
)

project_management_router = APIRouter()
project_management_router.include_router(project_router.router)
project_management_router.include_router(document_router.router)
project_management_router.include_router(state_router.router)
project_management_router.include_router(workspace_router.router)

__all__ = [
    "document_router",
    "get_chat_service_dep",
    "get_document_content_service_dep",
    "get_document_service_dep",
    "get_project_analysis_service_dep",
    "get_project_service_dep",
    "get_state_edit_service_dep",
    "get_workspace_composer_dep",
    "project_management_router",
    "project_router",
    "state_router",
    "workspace_router",
]
