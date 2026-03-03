"""Application service for diagram set creation and retrieval."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.diagram import AmbiguityReport, Diagram, DiagramSet, DiagramType
from app.services.diagram.ambiguity_detector import AmbiguityDetector
from app.services.diagram.diagram_generator import DiagramGenerator, GenerationResult
from app.services.diagram.llm_client import DiagramLLMClient

logger = logging.getLogger(__name__)
SEMVER_PART_COUNT = 3


class DiagramSetService:
    """Coordinates diagram set persistence and generation workflows."""

    async def create_diagram_set(
        self,
        *,
        session: AsyncSession,
        input_description: str,
        adr_id: str | None = None,
    ) -> dict[str, Any]:
        logger.info(
            "Creating diagram set with 3 parallel diagrams (description: %d chars, adr_id: %s)",
            len(input_description),
            adr_id,
        )
        llm_client = DiagramLLMClient()
        ambiguity_detector = AmbiguityDetector(llm_client)
        diagram_generator = DiagramGenerator(llm_client)

        try:
            diagram_set = DiagramSet(
                adr_id=adr_id,
                input_description=input_description,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(diagram_set)
            await session.flush()

            ambiguities_data = await ambiguity_detector.analyze_description(input_description)
            await self._store_ambiguities(session, diagram_set.id, ambiguities_data)

            functional_result, c4_context_result, c4_container_result = await asyncio.gather(
                diagram_generator.generate_mermaid_functional(description=input_description),
                diagram_generator.generate_c4_context(description=input_description),
                diagram_generator.generate_c4_container(description=input_description),
            )

            await self._store_generated_diagram(
                session,
                diagram_set.id,
                functional_result,
                DiagramType.MERMAID_FUNCTIONAL,
            )
            await self._store_generated_diagram(
                session,
                diagram_set.id,
                c4_context_result,
                DiagramType.C4_CONTEXT,
            )
            await self._store_generated_diagram(
                session,
                diagram_set.id,
                c4_container_result,
                DiagramType.C4_CONTAINER,
            )

            await session.commit()
            await session.refresh(diagram_set)
            return await self._build_response(session, diagram_set)
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("Error creating diagram set: %s", exc, exc_info=True)
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal server error: {exc!s}",
            ) from exc

    async def get_diagram_set(
        self,
        *,
        session: AsyncSession,
        diagram_set_id: str,
    ) -> dict[str, Any]:
        logger.info("Fetching diagram set: id=%s", diagram_set_id)
        stmt = select(DiagramSet).where(DiagramSet.id == diagram_set_id)
        result = await session.execute(stmt)
        diagram_set = result.scalar_one_or_none()
        if not diagram_set:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Diagram set {diagram_set_id} not found",
            )

        return await self._build_response(session, diagram_set)

    async def _store_ambiguities(
        self,
        session: AsyncSession,
        diagram_set_id: str,
        ambiguities_data: list[dict[str, Any]],
    ) -> None:
        for amb_data in ambiguities_data:
            ambiguity = AmbiguityReport(
                diagram_set_id=diagram_set_id,
                ambiguous_text=amb_data["ambiguous_text"],
                suggested_clarification=amb_data.get("suggested_clarification"),
                resolved=False,
                created_at=datetime.now(timezone.utc),
            )
            session.add(ambiguity)

    async def _store_generated_diagram(
        self,
        session: AsyncSession,
        diagram_set_id: str,
        gen_result: GenerationResult,
        diagram_type: DiagramType,
    ) -> None:
        if not gen_result.success:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    f"{diagram_type.value} generation failed after "
                    f"{gen_result.attempts} attempts: {gen_result.error}"
                ),
            )

        previous_stmt = (
            select(Diagram)
            .where(
                Diagram.diagram_set_id == diagram_set_id,
                Diagram.diagram_type == diagram_type.value,
            )
            .order_by(Diagram.created_at.desc())
            .limit(1)
        )
        previous_result = await session.execute(previous_stmt)
        previous_diagram = previous_result.scalar_one_or_none()

        version = "1.0.0"
        previous_version_id = None
        if previous_diagram:
            version = self._next_version(previous_diagram.version)
            previous_version_id = previous_diagram.id

        session.add(
            Diagram(
                diagram_set_id=diagram_set_id,
                diagram_type=diagram_type.value,
                source_code=gen_result.source_code,
                rendered_svg=None,
                rendered_png=None,
                version=version,
                previous_version_id=previous_version_id,
                created_at=datetime.now(timezone.utc),
            )
        )

    def _next_version(self, version: str) -> str:
        prefix = "v" if version.startswith("v") else ""
        core = version[1:] if prefix else version
        parts = core.split(".")
        if len(parts) != SEMVER_PART_COUNT:
            return f"{prefix}1.0.0"
        major, minor, patch = parts
        try:
            patch_int = int(patch)
        except ValueError:
            return f"{prefix}1.0.0"
        return f"{prefix}{major}.{minor}.{patch_int + 1}"

    async def _build_response(
        self,
        session: AsyncSession,
        diagram_set: DiagramSet,
    ) -> dict[str, Any]:
        diagrams_stmt = select(Diagram).where(Diagram.diagram_set_id == diagram_set.id)
        diagrams_result = await session.execute(diagrams_stmt)
        diagrams = diagrams_result.scalars().all()

        ambiguities_stmt = select(AmbiguityReport).where(
            AmbiguityReport.diagram_set_id == diagram_set.id
        )
        ambiguities_result = await session.execute(ambiguities_stmt)
        ambiguities = ambiguities_result.scalars().all()

        return {
            "id": diagram_set.id,
            "adr_id": diagram_set.adr_id,
            "input_description": diagram_set.input_description,
            "created_at": diagram_set.created_at.isoformat(),
            "updated_at": diagram_set.updated_at.isoformat(),
            "diagrams": [
                {
                    "id": d.id,
                    "diagram_set_id": d.diagram_set_id,
                    "diagram_type": d.diagram_type,
                    "source_code": d.source_code,
                    "version": d.version,
                    "created_at": d.created_at.isoformat(),
                }
                for d in diagrams
            ],
            "ambiguities": [
                {
                    "id": a.id,
                    "diagram_set_id": a.diagram_set_id,
                    "ambiguous_text": a.ambiguous_text,
                    "suggested_clarification": a.suggested_clarification,
                    "resolved": a.resolved,
                    "created_at": a.created_at.isoformat(),
                }
                for a in ambiguities
            ],
        }

