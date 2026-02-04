"""
Service for backfilling normalized WAF checklists from legacy ProjectState JSON.
"""

import random
from collections.abc import Callable
from typing import Any
from uuid import UUID

import json
import logging
from collections.abc import Callable
from typing import Any, AsyncContextManager
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents_system.checklists.engine import ChecklistEngine
from app.agents_system.checklists.normalize_helpers import validate_normalized_consistency
from app.models.checklist import Checklist
from app.models.project import Project, ProjectState

logger = logging.getLogger(__name__)

# Verification rate for random sampling
VERIFICATION_RATE = 0.01

class BackfillService:
    """
    Handles bulk backfill of projects from ProjectState to normalized DB.

    Features:
    - Idempotent chunked processing
    - Dry-run mode for validation
    - Progress tracking
    - Verification sampling
    """

    def __init__(
        self,
        engine: ChecklistEngine,
        db_session_factory: Callable[[], AsyncContextManager[AsyncSession]],
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
        """
        Backfill all projects with WAF checklists.

        Args:
            dry_run: If True, validate but don't write
            verify_sample: If True, validate random 1% sample

        Returns:
            Summary dict with counts and errors
        """
        summary = {
            "total_projects": 0,
            "processed": 0,
            "skipped": 0,
            "errors": [],
            "verification_passed": True,
            "verification_errors": [],
        }

        async with self.db_session_factory() as session:
            # Get all projects that have a WAF checklist in their state
            # Since state is a Text column (JSON string), we use a string check
            stmt = (
                select(Project.id)
                .join(ProjectState)
                .where(ProjectState.state.like('%"wafChecklist"%'))
            )
            result = await session.execute(stmt)
            project_ids = [row[0] for row in result.all()]

        summary["total_projects"] = len(project_ids)
        logger.info(f"Starting backfill: total={len(project_ids)}, dry_run={dry_run}")

        # Process in batches
        for i in range(0, len(project_ids), self.batch_size):
            batch = project_ids[i : i + self.batch_size]
            for project_id in batch:
                try:
                    res = await self.backfill_project(project_id, dry_run=dry_run)
                    if res.get("status") == "success":
                        summary["processed"] += 1

                        # Random verification
                        if verify_sample and random.random() < VERIFICATION_RATE:  # noqa: S311
                            is_consistent, diffs = await self.verify_project_consistency(project_id)
                            if not is_consistent:
                                summary["verification_passed"] = False
                                summary["verification_errors"].append({
                                    "project_id": str(project_id),
                                    "diffs": diffs
                                })
                                logger.warning(f"Verification failed: project_id={project_id}, diffs={diffs}")
                    else:
                        summary["skipped"] += 1
                except Exception as exc:
                    logger.exception(f"Backfill error: project_id={project_id}")
                    summary["errors"].append({"project_id": str(project_id), "error": str(exc)})

            logger.info(f"Backfill progress: processed={summary['processed']}, total={summary['total_projects']}")

        return summary

    async def backfill_project(self, project_id: UUID | str, dry_run: bool = False) -> dict[str, Any]:
        """Backfill single project."""
        p_id = str(project_id)
        async with self.db_session_factory() as session:
            stmt = select(ProjectState).where(ProjectState.project_id == p_id)
            result = await session.execute(stmt)
            project_state = result.scalar_one_or_none()

            if not project_state:
                return {"status": "skipped", "reason": "No ProjectState found"}
            
            # Parse state if it's a string
            state_dict = project_state.state
            if isinstance(state_dict, str):
                try:
                    state_dict = json.loads(state_dict)
                except json.JSONDecodeError:
                    return {"status": "error", "reason": "invalid_json_in_state"}

            if "wafChecklist" not in state_dict:
                return {"status": "skipped", "reason": "No WAF checklist in state"}

            # Sync to DB
            if not dry_run:
                # The engine handles its own session if we use sync_project_state_to_db
                await self.engine.sync_project_state_to_db(p_id, state_dict)
                return {"status": "success"}
            else:
                # Dry run: just validate
                return {"status": "success", "dry_run": True}

    async def verify_project_consistency(self, project_id: UUID | str) -> tuple[bool, list[str]]:
        """
        Verify normalized DB matches ProjectState JSON for a project.

        Args:
            project_id: Project UUID to verify

        Returns:
            (is_consistent, list_of_differences)
        """
        p_id = str(project_id)
        async with self.db_session_factory() as session:
            stmt = select(ProjectState).where(ProjectState.project_id == p_id)
            result = await session.execute(stmt)
            project_state = result.scalar_one_or_none()

            if not project_state:
                return True, []
            
            # Parse state if it's a string
            state_dict = project_state.state
            if isinstance(state_dict, str):
                try:
                    state_dict = json.loads(state_dict)
                except json.JSONDecodeError:
                    return False, ["Invalid JSON in project state"]

            if "wafChecklist" not in state_dict:
                return True, []

            # Reconstruct JSON from DB
            reconstructed_state = await self.engine.sync_db_to_project_state(p_id)

            # Compare
            is_consistent, diffs = validate_normalized_consistency(
                state_dict.get("wafChecklist", {}),
                reconstructed_state
            )

            return is_consistent, diffs

    async def get_backfill_progress(self) -> dict[str, Any]:
        """
        Get current backfill progress across all projects.

        Returns:
            Dict with total projects, migrated projects, percentage
        """
        async with self.db_session_factory() as session:
            # Count projects needing migration
            need_stmt = select(func.count(Project.id)).join(ProjectState).where(ProjectState.state.contains({"wafChecklist": {}}))
            total_needing = (await session.execute(need_stmt)).scalar() or 0

            # Count already migrated (have a Checklist record)
            done_stmt = select(func.count(Checklist.id))
            done_count = (await session.execute(done_stmt)).scalar() or 0

            return {
                "total_projects": total_needing,
                "migrated_projects": done_count,
                "percentage": (done_count / total_needing * 100) if total_needing > 0 else 100.0
            }
