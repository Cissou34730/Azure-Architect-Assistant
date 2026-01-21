"""Ambiguity resolution API endpoints.

Handles ambiguity detection results and resolution tracking for diagram generation.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.diagram import AmbiguityReport, DiagramSet
from app.services.diagram.database import get_diagram_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/diagram-sets", tags=["Ambiguities"])


# --- Request/Response Schemas ---


class AmbiguityReportResponse(BaseModel):
    """Response model for ambiguity report."""

    id: str
    diagram_set_id: str
    ambiguous_text: str
    suggested_clarification: str | None = None
    resolved: bool = False
    created_at: str

    model_config = {"from_attributes": True}


class ResolveAmbiguityRequest(BaseModel):
    """Request to mark ambiguity as resolved."""

    resolved: bool = Field(
        default=True, description="Mark as resolved (true) or unresolved (false)"
    )


# --- Endpoints ---


@router.get(
    "/{diagram_set_id}/ambiguities",
    response_model=list[AmbiguityReportResponse],
    summary="Get ambiguity reports for diagram set",
    description="List all detected ambiguities with resolution status (FR-019)",
)
async def get_ambiguities(
    diagram_set_id: str,
    resolved: bool | None = None,
    session: AsyncSession = Depends(get_diagram_session),
) -> list[AmbiguityReportResponse]:
    """Get ambiguity reports for a diagram set.

    Args:
        diagram_set_id: ID of diagram set
        resolved: Optional filter by resolution status (true/false)
        session: Database session

    Returns:
        List of ambiguity reports

    Raises:
        404: Diagram set not found
    """
    logger.info(
        "Fetching ambiguities for diagram_set_id=%s, resolved=%s",
        diagram_set_id,
        resolved,
    )

    # Verify diagram set exists
    stmt = select(DiagramSet).where(DiagramSet.id == diagram_set_id)
    result = await session.execute(stmt)
    diagram_set = result.scalar_one_or_none()

    if not diagram_set:
        logger.warning("Diagram set not found: %s", diagram_set_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Diagram set {diagram_set_id} not found",
        )

    # Build query for ambiguities
    stmt = select(AmbiguityReport).where(
        AmbiguityReport.diagram_set_id == diagram_set_id
    )

    if resolved is not None:
        stmt = stmt.where(AmbiguityReport.resolved == resolved)

    stmt = stmt.order_by(AmbiguityReport.created_at)

    result = await session.execute(stmt)
    ambiguities = result.scalars().all()

    logger.info(
        "Found %d ambiguities for diagram_set_id=%s", len(ambiguities), diagram_set_id
    )

    return [
        AmbiguityReportResponse(
            id=a.id,
            diagram_set_id=a.diagram_set_id,
            ambiguous_text=a.ambiguous_text,
            suggested_clarification=a.suggested_clarification,
            resolved=a.resolved,
            created_at=a.created_at.isoformat(),
        )
        for a in ambiguities
    ]


@router.patch(
    "/{diagram_set_id}/ambiguities/{ambiguity_id}/resolve",
    response_model=AmbiguityReportResponse,
    summary="Mark ambiguity as resolved",
    description="User acknowledges and resolves ambiguity (FR-006)",
)
async def resolve_ambiguity(
    diagram_set_id: str,
    ambiguity_id: str,
    request: ResolveAmbiguityRequest,
    session: AsyncSession = Depends(get_diagram_session),
) -> AmbiguityReportResponse:
    """Mark ambiguity as resolved or unresolved.

    Args:
        diagram_set_id: ID of diagram set
        ambiguity_id: ID of ambiguity report
        request: Resolution request with resolved flag
        session: Database session

    Returns:
        Updated ambiguity report

    Raises:
        404: Ambiguity not found or doesn't belong to diagram set
    """
    logger.info(
        "Resolving ambiguity: diagram_set_id=%s, ambiguity_id=%s, resolved=%s",
        diagram_set_id,
        ambiguity_id,
        request.resolved,
    )

    # Fetch ambiguity
    stmt = select(AmbiguityReport).where(
        AmbiguityReport.id == ambiguity_id,
        AmbiguityReport.diagram_set_id == diagram_set_id,
    )
    result = await session.execute(stmt)
    ambiguity = result.scalar_one_or_none()

    if not ambiguity:
        logger.warning(
            "Ambiguity not found: %s (diagram_set_id=%s)", ambiguity_id, diagram_set_id
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ambiguity {ambiguity_id} not found in diagram set {diagram_set_id}",
        )

    # Update resolution status
    ambiguity.resolved = request.resolved
    await session.commit()
    await session.refresh(ambiguity)

    logger.info("Ambiguity %s marked as resolved=%s", ambiguity_id, request.resolved)

    return AmbiguityReportResponse(
        id=ambiguity.id,
        diagram_set_id=ambiguity.diagram_set_id,
        ambiguous_text=ambiguity.ambiguous_text,
        suggested_clarification=ambiguity.suggested_clarification,
        resolved=ambiguity.resolved,
        created_at=ambiguity.created_at.isoformat(),
    )

