"""Diagram set CRUD API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.diagram.database import get_diagram_session
from app.services.diagram.diagram_set_service import DiagramSetService

from .schemas import AmbiguityReportResponse

router = APIRouter(prefix="/diagram-sets", tags=["Diagrams"])
diagram_set_service = DiagramSetService()


class CreateDiagramSetRequest(BaseModel):
    """Request to create new diagram set."""

    input_description: str = Field(
        ...,
        min_length=10,
        max_length=50000,
        description="Functional requirements or technical design description",
    )
    adr_id: str | None = Field(
        None,
        pattern=r"^[A-Za-z0-9-]+$",
        description="Optional ADR identifier to link diagrams",
    )


class DiagramResponse(BaseModel):
    """Response model for individual diagram."""

    id: str
    diagram_set_id: str
    diagram_type: str
    source_code: str
    version: str
    created_at: str


class DiagramSetResponse(BaseModel):
    """Response model for complete diagram set."""

    id: str
    adr_id: str | None = None
    input_description: str
    created_at: str
    updated_at: str
    diagrams: list[DiagramResponse]
    ambiguities: list[AmbiguityReportResponse]


@router.post(
    "",
    response_model=DiagramSetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new diagram set with generation",
    description=(
        "Generate diagrams from input description. Creates DiagramSet, detects "
        "ambiguities, and generates Mermaid/C4 diagrams."
    ),
)
async def create_diagram_set(
    request: CreateDiagramSetRequest,
    session: AsyncSession = Depends(get_diagram_session),
) -> DiagramSetResponse:
    result = await diagram_set_service.create_diagram_set(
        session=session,
        input_description=request.input_description,
        adr_id=request.adr_id,
    )
    return DiagramSetResponse.model_validate(result)


@router.get(
    "/{diagram_set_id}",
    response_model=DiagramSetResponse,
    summary="Get diagram set by ID",
    description="Retrieve a single diagram set with all diagrams and ambiguities (FR-012)",
)
async def get_diagram_set(
    diagram_set_id: str,
    session: AsyncSession = Depends(get_diagram_session),
) -> DiagramSetResponse:
    result = await diagram_set_service.get_diagram_set(
        session=session,
        diagram_set_id=diagram_set_id,
    )
    return DiagramSetResponse.model_validate(result)
