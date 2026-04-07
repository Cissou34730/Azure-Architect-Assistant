"""Backfill service for checklist bootstrap operations."""

from __future__ import annotations

import logging
import random
from collections.abc import Callable
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.checklists.infrastructure.engine import ChecklistEngine
from app.features.checklists.infrastructure.models import Checklist
from app.models.project import Project, ProjectState

logger = logging.getLogger(__name__)

VERIFICATION_RATE = 0.01


class BackfillService:
    """Bulk bootstrap/verification operations for normalized checklists."""

    def __init__(
        self,
        engine: ChecklistEngine,
        db_session_factory: Callable[[], AsyncSession],
        batch_size: int = 50,
    ) -> None:
        self.engine = engine
        self.db_session_factory = db_session_factory
        self.batch_size = batch_size

    async def backfill_all_projects(
        self,
        dry_run: bool = False,
        verify_sample: bool = True,
    ) -> dict[str, Any]:
        summary: dict[str, Any] = {
            "total_projects": 0,
            "processed": 0,
            "skipped": 0,
            "errors": [],
            "verification_passed": True,
            "verification_errors": [],
        }

        project_ids = await self._find_project_ids()
        summary["total_projects"] = len(project_ids)
        logger.info("Starting checklist bootstrap backfill: total=%s dry_run=%s", len(project_ids), dry_run)

        for i in range(0, len(project_ids), self.batch_size):
            batch = project_ids[i : i + self.batch_size]
            for project_id in batch:
                try:
                    result = await self.backfill_project(project_id, dry_run=dry_run)
                    if result.get("status") == "success":
                        summary["processed"] += 1
                        if verify_sample and random.random() < VERIFICATION_RATE:  # noqa: S311
                            ok, diffs = await self.verify_project_consistency(project_id)
                            if not ok:
                                summary["verification_passed"] = False
                                summary["verification_errors"].append(
                                    {"project_id": str(project_id), "diffs": diffs}
                                )
                    else:
                        summary["skipped"] += 1
                except Exception as exc:
                    logger.exception("Backfill error for project %s", project_id)
                    summary["errors"].append({"project_id": str(project_id), "error": str(exc)})

            logger.info(
                "Backfill progress: processed=%s/%s",
                summary["processed"],
                summary["total_projects"],
            )

        return summary

    async def backfill_project(self, project_id: UUID | str, dry_run: bool = False) -> dict[str, Any]:
        """Ensure normalized checklists exist for a single project."""
        project_id_str = str(project_id)
        async with self.db_session_factory() as session:
            project = (
                await session.execute(select(Project).where(Project.id == project_id_str))
            ).scalar_one_or_none()
            if project is None:
                return {"status": "skipped", "reason": "project_not_found"}

        if dry_run:
            return {"status": "success", "dry_run": True}

        checklists = await self.engine.ensure_project_checklists(project_id_str, None)
        return {"status": "success", "checklists_ensured": len(checklists)}

    async def verify_project_consistency(self, project_id: UUID | str) -> tuple[bool, list[str]]:
        """Verify a project has at least one normalized checklist."""
        project_id_str = str(project_id)
        async with self.db_session_factory() as session:
            checklist_count = (
                await session.execute(
                    select(func.count(Checklist.id)).where(Checklist.project_id == project_id_str)
                )
            ).scalar() or 0
        if checklist_count > 0:
            return True, []
        return False, ["no_normalized_checklists"]

    async def get_backfill_progress(self) -> dict[str, Any]:
        """Return high-level checklist bootstrap progress metrics."""
        async with self.db_session_factory() as session:
            total_projects = (
                await session.execute(
                    select(func.count(Project.id))
                    .join(ProjectState, ProjectState.project_id == Project.id)
                )
            ).scalar() or 0

            migrated_projects = (
                await session.execute(select(func.count(func.distinct(Checklist.project_id))))
            ).scalar() or 0

        percentage = (migrated_projects / total_projects * 100) if total_projects else 100.0
        return {
            "total_projects": int(total_projects),
            "migrated_projects": int(migrated_projects),
            "percentage": percentage,
        }

    async def _find_project_ids(self) -> list[str]:
        async with self.db_session_factory() as session:
            result = await session.execute(
                select(Project.id)
                .join(ProjectState, ProjectState.project_id == Project.id)
            )
            return [str(row[0]) for row in result.all()]

