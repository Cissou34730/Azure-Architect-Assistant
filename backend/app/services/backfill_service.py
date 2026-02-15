"""Backfill service for migrating legacy WAF JSON into normalized checklist tables."""

from __future__ import annotations

import json
import logging
import random
from collections.abc import Callable
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents_system.checklists.engine import ChecklistEngine
from app.agents_system.checklists.normalize_helpers import validate_normalized_consistency
from app.models.checklist import Checklist
from app.models.project import Project, ProjectState

logger = logging.getLogger(__name__)

VERIFICATION_RATE = 0.01


class BackfillService:
    """Bulk backfill/verification operations for normalized WAF checklists."""

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

        project_ids = await self._find_projects_with_waf()
        summary["total_projects"] = len(project_ids)
        logger.info("Starting checklist backfill: total=%s dry_run=%s", len(project_ids), dry_run)

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
        """Backfill a single project's WAF checklist payload."""
        project_id_str = str(project_id)
        async with self.db_session_factory() as session:
            project_state = (
                await session.execute(
                    select(ProjectState).where(ProjectState.project_id == project_id_str)
                )
            ).scalar_one_or_none()

            if project_state is None:
                return {"status": "skipped", "reason": "project_state_not_found"}

            state_dict = self._parse_state(project_state.state)
            if state_dict is None:
                return {"status": "error", "reason": "invalid_json_in_state"}
            if "wafChecklist" not in state_dict:
                return {"status": "skipped", "reason": "no_waf_checklist"}

        if dry_run:
            return {"status": "success", "dry_run": True}

        return await self.engine.sync_project_state_to_db(project_id_str, state_dict)

    async def verify_project_consistency(self, project_id: UUID | str) -> tuple[bool, list[str]]:
        """Compare legacy state WAF payload with reconstructed payload from normalized DB."""
        project_id_str = str(project_id)
        async with self.db_session_factory() as session:
            project_state = (
                await session.execute(
                    select(ProjectState).where(ProjectState.project_id == project_id_str)
                )
            ).scalar_one_or_none()

            if project_state is None:
                return True, []

            state_dict = self._parse_state(project_state.state)
            if state_dict is None:
                return False, ["invalid_json_in_state"]

            raw_waf = state_dict.get("wafChecklist")
            if not isinstance(raw_waf, dict):
                return True, []

        reconstructed = await self.engine.sync_db_to_project_state(project_id_str)
        return validate_normalized_consistency(raw_waf, reconstructed)

    async def get_backfill_progress(self) -> dict[str, Any]:
        """Return high-level migration progress metrics."""
        async with self.db_session_factory() as session:
            total_projects = (
                await session.execute(
                    select(func.count(Project.id))
                    .join(ProjectState, ProjectState.project_id == Project.id)
                    .where(ProjectState.state.like('%"wafChecklist"%'))
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

    async def _find_projects_with_waf(self) -> list[str]:
        async with self.db_session_factory() as session:
            result = await session.execute(
                select(Project.id)
                .join(ProjectState, ProjectState.project_id == Project.id)
                .where(ProjectState.state.like('%"wafChecklist"%'))
            )
            return [str(row[0]) for row in result.all()]

    def _parse_state(self, raw_state: str | dict[str, Any]) -> dict[str, Any] | None:
        if isinstance(raw_state, dict):
            return raw_state
        try:
            return json.loads(raw_state)
        except (TypeError, json.JSONDecodeError):
            return None
