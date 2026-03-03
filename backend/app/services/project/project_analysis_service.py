"""Project analysis orchestration service."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.diagram.project_diagram_helpers import (
    append_diagram_reference_to_project_state,
    ensure_initial_c4_context_diagram,
)
from app.services.project.document_service import DocumentService

logger = logging.getLogger(__name__)


class ProjectAnalysisService:
    """Coordinates document analysis with optional diagram bootstrap."""

    def __init__(self, document_service: DocumentService) -> None:
        self.document_service = document_service

    async def analyze_documents_with_bootstrap(
        self,
        *,
        project_id: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        state = await self.document_service.analyze_documents(project_id, db)

        try:
            diagram_ref = await ensure_initial_c4_context_diagram(project_id, state)
            if diagram_ref is not None:
                state = await append_diagram_reference_to_project_state(
                    project_id, state, diagram_ref, db
                )
        except Exception:
            logger.exception(
                "C4 context diagram generation skipped for project %s",
                project_id,
            )

        return state

