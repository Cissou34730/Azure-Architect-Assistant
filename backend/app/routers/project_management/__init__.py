"""
Project Management API
Modular router for project lifecycle management.
Aggregates project CRUD, document, and state/proposal sub-routers.
"""

from fastapi import APIRouter

from . import document_router, project_router, state_router

project_management_router = APIRouter()
project_management_router.include_router(project_router.router)
project_management_router.include_router(document_router.router)
project_management_router.include_router(state_router.router)

__all__ = ["project_management_router", "project_router"]

