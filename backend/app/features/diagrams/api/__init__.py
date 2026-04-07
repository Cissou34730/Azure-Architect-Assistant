"""Diagram generation router aggregation."""

from fastapi import APIRouter

from .ambiguities import router as ambiguities_router
from .diagram_sets import router as diagram_sets_router

diagram_generation_router = APIRouter(
    tags=["Diagram Generation"],
    responses={404: {"description": "Not found"}},
)

diagram_generation_router.include_router(diagram_sets_router)
diagram_generation_router.include_router(ambiguities_router)

__all__ = ["diagram_generation_router"]
