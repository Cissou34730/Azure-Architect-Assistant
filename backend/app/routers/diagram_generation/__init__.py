"""Diagram generation router aggregation."""

from fastapi import APIRouter
from .diagram_sets import router as diagram_sets_router
from .ambiguities import router as ambiguities_router

router = APIRouter(
    tags=["Diagram Generation"],
    responses={404: {"description": "Not found"}},
)

# Include sub-routers
router.include_router(diagram_sets_router)
router.include_router(ambiguities_router)

# Locks router to be added in Phase 7 (US5)
# from .locks import router as locks_router
# router.include_router(locks_router)
