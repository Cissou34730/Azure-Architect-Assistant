"""
Project Management API
Modular router for project lifecycle management.
Aggregates project CRUD, document, and state/proposal sub-routers.
"""

from fastapi import APIRouter

from .document_router import router as _document_router
from .project_router import router as _project_router
from .state_router import router as _state_router

router = APIRouter()
router.include_router(_project_router)
router.include_router(_document_router)
router.include_router(_state_router)

__all__ = ["router"]

