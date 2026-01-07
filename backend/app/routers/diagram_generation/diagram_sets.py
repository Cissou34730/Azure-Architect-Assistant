"""Diagram set CRUD API endpoints.

Main entry point for diagram generation from architecture descriptions.
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field

from app.models.diagram import DiagramSet, Diagram, AmbiguityReport, DiagramType
from app.services.diagram.database import get_diagram_session
from app.services.diagram.llm_client import DiagramLLMClient
from app.services.diagram.ambiguity_detector import AmbiguityDetector
from app.services.diagram.diagram_generator import DiagramGenerator, GenerationResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/diagram-sets", tags=["Diagrams"])


# --- Request/Response Schemas ---


class CreateDiagramSetRequest(BaseModel):
    """Request to create new diagram set."""

    input_description: str = Field(
        ...,
        min_length=10,
        max_length=50000,
        description="Functional requirements or technical design description",
    )
    adr_id: Optional[str] = Field(
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

    model_config = {"from_attributes": True}


class AmbiguityReportResponse(BaseModel):
    """Response model for ambiguity report."""

    id: str
    diagram_set_id: str
    ambiguous_text: str
    suggested_clarification: Optional[str] = None
    resolved: bool = False
    created_at: str

    model_config = {"from_attributes": True}


class DiagramSetResponse(BaseModel):
    """Response model for complete diagram set."""

    id: str
    adr_id: Optional[str] = None
    input_description: str
    created_at: str
    updated_at: str
    diagrams: List[DiagramResponse]
    ambiguities: List[AmbiguityReportResponse]


# --- Helper Functions ---


def _get_llm_client() -> DiagramLLMClient:
    """Get diagram-specific LLM client (dependency injection)."""
    # DiagramLLMClient loads settings internally via get_app_settings() and get_openai_settings()
    return DiagramLLMClient()


async def _store_ambiguities(
    session: AsyncSession, diagram_set_id: str, ambiguities_data: List[Dict[str, Any]]
) -> None:
    """Store detected ambiguities in database.

    Args:
        session: Database session
        diagram_set_id: ID of parent diagram set
        ambiguities_data: List of ambiguity dictionaries from detector
    """
    for amb_data in ambiguities_data:
        ambiguity = AmbiguityReport(
            diagram_set_id=diagram_set_id,
            ambiguous_text=amb_data["ambiguous_text"],
            suggested_clarification=amb_data.get("suggested_clarification"),
            resolved=False,
            created_at=datetime.now(timezone.utc),
        )
        session.add(ambiguity)

    logger.info("Created %d ambiguity reports", len(ambiguities_data))


async def _store_generated_diagram(
    session: AsyncSession,
    diagram_set_id: str,
    gen_result: GenerationResult,
    diagram_type: DiagramType,
) -> None:
    """Store generated diagram in database.

    Args:
        session: Database session
        diagram_set_id: ID of parent diagram set
        gen_result: Generation result from diagram generator
        diagram_type: Type of diagram being stored

    Raises:
        HTTPException: If generation failed
    """
    if not gen_result.success:
        logger.error(
            "Diagram generation failed for %s: %s", diagram_type.value, gen_result.error
        )
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{diagram_type.value} generation failed after {gen_result.attempts} attempts: {gen_result.error}",
        )

    diagram = Diagram(
        diagram_set_id=diagram_set_id,
        diagram_type=diagram_type.value,  # Convert enum to string
        source_code=gen_result.source_code,
        rendered_svg=None,  # Mermaid rendered client-side
        rendered_png=None,
        version="1.0.0",  # Initial version
        created_at=datetime.now(timezone.utc),
    )
    session.add(diagram)
    logger.info("Generated %s diagram (version 1.0.0)", diagram_type.value)


async def _build_response(
    session: AsyncSession, diagram_set: DiagramSet
) -> DiagramSetResponse:
    """Build complete diagram set response with diagrams and ambiguities.

    Args:
        session: Database session
        diagram_set: DiagramSet entity

    Returns:
        Complete DiagramSetResponse
    """
    # Fetch diagrams
    diagrams_stmt = select(Diagram).where(Diagram.diagram_set_id == diagram_set.id)
    diagrams_result = await session.execute(diagrams_stmt)
    diagrams = diagrams_result.scalars().all()

    # Fetch ambiguities
    ambiguities_stmt = select(AmbiguityReport).where(
        AmbiguityReport.diagram_set_id == diagram_set.id
    )
    ambiguities_result = await session.execute(ambiguities_stmt)
    ambiguities = ambiguities_result.scalars().all()

    logger.info(
        "DiagramSet created successfully: id=%s, diagrams=%d, ambiguities=%d",
        diagram_set.id,
        len(diagrams),
        len(ambiguities),
    )

    return DiagramSetResponse(
        id=diagram_set.id,
        adr_id=diagram_set.adr_id,
        input_description=diagram_set.input_description,
        created_at=diagram_set.created_at.isoformat(),
        updated_at=diagram_set.updated_at.isoformat(),
        diagrams=[
            DiagramResponse(
                id=d.id,
                diagram_set_id=d.diagram_set_id,
                diagram_type=d.diagram_type,  # Already a string from DB
                source_code=d.source_code,
                version=d.version,
                created_at=d.created_at.isoformat(),
            )
            for d in diagrams
        ],
        ambiguities=[
            AmbiguityReportResponse(
                id=a.id,
                diagram_set_id=a.diagram_set_id,
                ambiguous_text=a.ambiguous_text,
                suggested_clarification=a.suggested_clarification,
                resolved=a.resolved,
                created_at=a.created_at.isoformat(),
            )
            for a in ambiguities
        ],
    )


# --- Endpoints ---


@router.post(
    "",
    response_model=DiagramSetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new diagram set with generation",
    description="Generate diagrams from input description. Creates DiagramSet, detects ambiguities, generates 3 Mermaid diagrams in parallel: functional flow, C4 Context, and C4 Container (FR-001, FR-002, FR-003, FR-004)",
)
async def create_diagram_set(
    request: CreateDiagramSetRequest,
    session: AsyncSession = Depends(get_diagram_session),
) -> DiagramSetResponse:
    """Create diagram set and generate diagrams.

    Flow:
    1. Create DiagramSet record
    2. Detect ambiguities
    3. Generate 3 diagrams in parallel (US1 + US2):
       - Mermaid functional flow diagram
       - C4 Context diagram (system boundaries)
       - C4 Container diagram (application architecture)
    4. Store results in database
    5. Return complete diagram set

    Args:
        request: Creation request with description and optional ADR ID
        session: Database session

    Returns:
        DiagramSetResponse with 3 generated diagrams and detected ambiguities

    Raises:
        400: Invalid input description
        500: Generation failed after retries
    """
    logger.info(
        "Creating diagram set with 3 parallel diagrams (description: %d chars, adr_id: %s)",
        len(request.input_description),
        request.adr_id,
    )

    # Initialize services
    llm_client = _get_llm_client()
    ambiguity_detector = AmbiguityDetector(llm_client)
    diagram_generator = DiagramGenerator(llm_client)

    try:
        # Create DiagramSet record
        diagram_set = DiagramSet(
            adr_id=request.adr_id,
            input_description=request.input_description,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(diagram_set)
        await session.flush()  # Get ID without committing
        logger.info("Created DiagramSet with id=%s", diagram_set.id)

        # Detect and store ambiguities
        ambiguities_data = await ambiguity_detector.analyze_description(
            request.input_description
        )
        await _store_ambiguities(session, diagram_set.id, ambiguities_data)

        # Generate 3 diagrams in parallel (Phase 4: US2)
        logger.info("Generating 3 diagrams in parallel")
        (
            functional_result,
            c4_context_result,
            c4_container_result,
        ) = await asyncio.gather(
            diagram_generator.generate_mermaid_functional(
                description=request.input_description
            ),
            diagram_generator.generate_c4_context(
                description=request.input_description
            ),
            diagram_generator.generate_c4_container(
                description=request.input_description
            ),
        )

        # Store all 3 diagrams
        await _store_generated_diagram(
            session, diagram_set.id, functional_result, DiagramType.MERMAID_FUNCTIONAL
        )
        await _store_generated_diagram(
            session, diagram_set.id, c4_context_result, DiagramType.C4_CONTEXT
        )
        await _store_generated_diagram(
            session, diagram_set.id, c4_container_result, DiagramType.C4_CONTAINER
        )

        # Commit and return response
        await session.commit()
        await session.refresh(diagram_set)
        return await _build_response(session, diagram_set)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating diagram set: %s", str(e), exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.get(
    "/{diagram_set_id}",
    response_model=DiagramSetResponse,
    summary="Get diagram set by ID",
    description="Retrieve a single diagram set with all diagrams and ambiguities (FR-012)",
)
async def get_diagram_set(
    diagram_set_id: str, session: AsyncSession = Depends(get_diagram_session)
) -> DiagramSetResponse:
    """Get diagram set by ID.

    Args:
        diagram_set_id: ID of diagram set
        session: Database session

    Returns:
        DiagramSetResponse with all diagrams and ambiguities

    Raises:
        404: Diagram set not found
    """
    logger.info("Fetching diagram set: id=%s", diagram_set_id)

    # Fetch diagram set
    stmt = select(DiagramSet).where(DiagramSet.id == diagram_set_id)
    result = await session.execute(stmt)
    diagram_set = result.scalar_one_or_none()

    if not diagram_set:
        logger.warning("Diagram set not found: %s", diagram_set_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Diagram set {diagram_set_id} not found",
        )

    # Fetch diagrams
    diagrams_stmt = select(Diagram).where(Diagram.diagram_set_id == diagram_set_id)
    diagrams_result = await session.execute(diagrams_stmt)
    diagrams = diagrams_result.scalars().all()

    # Fetch ambiguities
    ambiguities_stmt = select(AmbiguityReport).where(
        AmbiguityReport.diagram_set_id == diagram_set_id
    )
    ambiguities_result = await session.execute(ambiguities_stmt)
    ambiguities = ambiguities_result.scalars().all()

    logger.info(
        "Fetched diagram set: id=%s, diagrams=%d, ambiguities=%d",
        diagram_set_id,
        len(diagrams),
        len(ambiguities),
    )

    return DiagramSetResponse(
        id=diagram_set.id,
        adr_id=diagram_set.adr_id,
        input_description=diagram_set.input_description,
        created_at=diagram_set.created_at.isoformat(),
        updated_at=diagram_set.updated_at.isoformat(),
        diagrams=[
            DiagramResponse(
                id=d.id,
                diagram_set_id=d.diagram_set_id,
                diagram_type=d.diagram_type,  # Already a string from DB
                source_code=d.source_code,
                version=d.version,
                created_at=d.created_at.isoformat(),
            )
            for d in diagrams
        ],
        ambiguities=[
            AmbiguityReportResponse(
                id=a.id,
                diagram_set_id=a.diagram_set_id,
                ambiguous_text=a.ambiguous_text,
                suggested_clarification=a.suggested_clarification,
                resolved=a.resolved,
                created_at=a.created_at.isoformat(),
            )
            for a in ambiguities
        ],
    )
