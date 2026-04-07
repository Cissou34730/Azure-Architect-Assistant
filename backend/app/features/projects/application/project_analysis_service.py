"""Project analysis orchestration service."""

from __future__ import annotations

import logging
from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from .document_service import DocumentService

logger = logging.getLogger(__name__)


class DiagramBootstrapper(Protocol):
    async def ensure_initial_context_diagram(
        self,
        project_id: str,
        state: dict[str, Any],
    ) -> dict[str, Any] | None: ...

    async def append_diagram_reference(
        self,
        project_id: str,
        state: dict[str, Any],
        diagram_ref: dict[str, Any],
        db: AsyncSession,
    ) -> dict[str, Any]: ...


class _NoopDiagramBootstrapper:
    async def ensure_initial_context_diagram(
        self,
        project_id: str,
        state: dict[str, Any],
    ) -> dict[str, Any] | None:
        return None

    async def append_diagram_reference(
        self,
        project_id: str,
        state: dict[str, Any],
        diagram_ref: dict[str, Any],
        db: AsyncSession,
    ) -> dict[str, Any]:
        return state


class ProjectAnalysisService:
    """Coordinates document analysis with optional diagram bootstrap."""

    def __init__(
        self,
        document_service: DocumentService,
        diagram_bootstrapper: DiagramBootstrapper | None = None,
    ) -> None:
        self.document_service = document_service
        self._diagram_bootstrapper = (
            diagram_bootstrapper if diagram_bootstrapper is not None else _NoopDiagramBootstrapper()
        )

    async def analyze_documents_with_bootstrap(
        self,
        *,
        project_id: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        state = await self.document_service.analyze_documents(project_id, db)

        try:
            diagram_ref = await self._diagram_bootstrapper.ensure_initial_context_diagram(
                project_id,
                state,
            )
            if diagram_ref is not None:
                state = await self._diagram_bootstrapper.append_diagram_reference(
                    project_id, state, diagram_ref, db
                )
        except Exception:
            logger.exception(
                "C4 context diagram generation skipped for project %s",
                project_id,
            )

        return state

