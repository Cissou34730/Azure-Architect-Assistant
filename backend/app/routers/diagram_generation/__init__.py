"""Diagram generation router aggregation."""

from fastapi import APIRouter

# Import sub-routers (will be created in subsequent tasks)
# from .diagram_sets import router as diagram_sets_router
# from .ambiguities import router as ambiguities_router
# from .locks import router as locks_router

router = APIRouter(
    tags=["Diagram Generation"],
    responses={404: {"description": "Not found"}},
)

# Include sub-routers when they are implemented
# router.include_router(diagram_sets_router)
# router.include_router(ambiguities_router)
# router.include_router(locks_router)
