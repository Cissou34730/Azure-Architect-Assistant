"""Service boundary for diagram ambiguity read/write operations."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.diagram import AmbiguityReport, DiagramSet


class AmbiguityService:
    """Persistence operations for ambiguity endpoints."""

    async def list_ambiguities(
        self,
        *,
        diagram_set_id: str,
        session: AsyncSession,
        resolved: bool | None = None,
    ) -> list[AmbiguityReport]:
        set_stmt = select(DiagramSet).where(DiagramSet.id == diagram_set_id)
        set_result = await session.execute(set_stmt)
        diagram_set = set_result.scalar_one_or_none()
        if diagram_set is None:
            raise ValueError("Diagram set not found")

        stmt = select(AmbiguityReport).where(AmbiguityReport.diagram_set_id == diagram_set_id)
        if resolved is not None:
            stmt = stmt.where(AmbiguityReport.resolved == resolved)
        stmt = stmt.order_by(AmbiguityReport.created_at)

        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def resolve_ambiguity(
        self,
        *,
        diagram_set_id: str,
        ambiguity_id: str,
        resolved: bool,
        session: AsyncSession,
    ) -> AmbiguityReport:
        stmt = select(AmbiguityReport).where(
            AmbiguityReport.id == ambiguity_id,
            AmbiguityReport.diagram_set_id == diagram_set_id,
        )
        result = await session.execute(stmt)
        ambiguity = result.scalar_one_or_none()
        if ambiguity is None:
            raise ValueError("Ambiguity not found")

        ambiguity.resolved = resolved
        await session.commit()
        await session.refresh(ambiguity)
        return ambiguity


ambiguity_service = AmbiguityService()
