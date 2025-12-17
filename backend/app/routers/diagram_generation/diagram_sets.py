"""Diagram set CRUD API endpoints.

Main entry point for diagram generation from architecture descriptions.
"""

import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field

from app.models.diagram import DiagramSet, Diagram, AmbiguityReport, DiagramType
from app.services.diagram.database import get_diagram_session
from app.services.diagram.llm_client import DiagramLLMClient
from app.services.diagram.ambiguity_detector import AmbiguityDetector
from app.services.diagram.diagram_generator import DiagramGenerator
from app.core.config import get_app_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/diagram-sets", tags=["Diagrams"])


# --- Request/Response Schemas ---

class CreateDiagramSetRequest(BaseModel):
    """Request to create new diagram set."""
    input_description: str = Field(
        ...,
        min_length=10,
        max_length=50000,
        description="Functional requirements or technical design description"
    )
    adr_id: Optional[str] = Field(
        None,
        pattern=r'^[A-Za-z0-9-]+$',
        description="Optional ADR identifier to link diagrams"
    )


class DiagramResponse(BaseModel):
    """Response model for individual diagram."""
    id: str
    diagram_set_id: str
    diagram_type: str
    source_code: str
    version: str
    created_at: str
    
    class Config:
        from_attributes = True


class AmbiguityReportResponse(BaseModel):
    """Response model for ambiguity report."""
    id: str
    diagram_set_id: str
    ambiguous_text: str
    suggested_clarification: Optional[str] = None
    resolved: bool = False
    created_at: str
    
    class Config:
        from_attributes = True


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


# --- Endpoints ---

@router.post(
    "",
    response_model=DiagramSetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new diagram set with generation",
    description="Generate diagrams from input description. Creates DiagramSet, detects ambiguities, generates Mermaid functional diagram (FR-001, FR-002, FR-003)"
)
async def create_diagram_set(
    request: CreateDiagramSetRequest,
    session: AsyncSession = Depends(get_diagram_session)
) -> DiagramSetResponse:
    """Create diagram set and generate diagrams.
    
    Flow:
    1. Create DiagramSet record
    2. Detect ambiguities in parallel with diagram generation
    3. Generate Mermaid functional diagram (US1)
    4. Store results in database
    5. Return complete diagram set
    
    Args:
        request: Creation request with description and optional ADR ID
        session: Database session
        
    Returns:
        DiagramSetResponse with generated diagrams and detected ambiguities
        
    Raises:
        400: Invalid input description
        500: Generation failed after retries
    """
    logger.info(
        "Creating diagram set (description: %d chars, adr_id: %s)",
        len(request.input_description), request.adr_id
    )
    
    # Initialize services
    llm_client = _get_llm_client()
    ambiguity_detector = AmbiguityDetector(llm_client)
    diagram_generator = DiagramGenerator(llm_client)
    
    try:
        # Step 1: Create DiagramSet
        diagram_set = DiagramSet(
            adr_id=request.adr_id,
            input_description=request.input_description,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(diagram_set)
        await session.flush()  # Get ID without committing
        
        logger.info("Created DiagramSet with id=%s", diagram_set.id)
        
        # Step 2: Detect ambiguities (non-blocking)
        ambiguities_data = await ambiguity_detector.analyze_description(request.input_description)
        
        # Store ambiguity reports
        for amb_data in ambiguities_data:
            ambiguity = AmbiguityReport(
                diagram_set_id=diagram_set.id,
                ambiguous_text=amb_data["ambiguous_text"],
                suggested_clarification=amb_data.get("suggested_clarification"),
                resolved=False,
                created_at=datetime.utcnow()
            )
            session.add(ambiguity)
        
        logger.info("Created %d ambiguity reports", len(ambiguities_data))
        
        # Step 3: Generate Mermaid functional diagram (US1)
        gen_result = await diagram_generator.generate_mermaid_functional(
            description=request.input_description
        )
        
        if not gen_result.success:
            logger.error("Diagram generation failed: %s", gen_result.error)
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Diagram generation failed after {gen_result.attempts} attempts: {gen_result.error}"
            )
        
        # Store generated diagram
        diagram = Diagram(
            diagram_set_id=diagram_set.id,
            diagram_type=DiagramType.MERMAID_FUNCTIONAL,
            source_code=gen_result.source_code,
            rendered_svg=None,  # Mermaid rendered client-side
            rendered_png=None,
            version="1.0.0",  # Initial version
            created_at=datetime.utcnow()
        )
        session.add(diagram)
        
        logger.info("Generated Mermaid functional diagram (version 1.0.0)")
        
        # Step 4: Commit all changes
        await session.commit()
        await session.refresh(diagram_set)
        
        # Step 5: Build response
        # Fetch diagrams and ambiguities
        diagrams_stmt = select(Diagram).where(Diagram.diagram_set_id == diagram_set.id)
        diagrams_result = await session.execute(diagrams_stmt)
        diagrams = diagrams_result.scalars().all()
        
        ambiguities_stmt = select(AmbiguityReport).where(AmbiguityReport.diagram_set_id == diagram_set.id)
        ambiguities_result = await session.execute(ambiguities_stmt)
        ambiguities = ambiguities_result.scalars().all()
        
        logger.info(
            "DiagramSet created successfully: id=%s, diagrams=%d, ambiguities=%d",
            diagram_set.id, len(diagrams), len(ambiguities)
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
                    diagram_type=d.diagram_type.value,
                    source_code=d.source_code,
                    version=d.version,
                    created_at=d.created_at.isoformat()
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
                    created_at=a.created_at.isoformat()
                )
                for a in ambiguities
            ]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating diagram set: %s", str(e), exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/{diagram_set_id}",
    response_model=DiagramSetResponse,
    summary="Get diagram set by ID",
    description="Retrieve a single diagram set with all diagrams and ambiguities (FR-012)"
)
async def get_diagram_set(
    diagram_set_id: str,
    session: AsyncSession = Depends(get_diagram_session)
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
            detail=f"Diagram set {diagram_set_id} not found"
        )
    
    # Fetch diagrams
    diagrams_stmt = select(Diagram).where(Diagram.diagram_set_id == diagram_set_id)
    diagrams_result = await session.execute(diagrams_stmt)
    diagrams = diagrams_result.scalars().all()
    
    # Fetch ambiguities
    ambiguities_stmt = select(AmbiguityReport).where(AmbiguityReport.diagram_set_id == diagram_set_id)
    ambiguities_result = await session.execute(ambiguities_stmt)
    ambiguities = ambiguities_result.scalars().all()
    
    logger.info(
        "Fetched diagram set: id=%s, diagrams=%d, ambiguities=%d",
        diagram_set_id, len(diagrams), len(ambiguities)
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
                diagram_type=d.diagram_type.value,
                source_code=d.source_code,
                version=d.version,
                created_at=d.created_at.isoformat()
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
                created_at=a.created_at.isoformat()
            )
            for a in ambiguities
        ]
    )
