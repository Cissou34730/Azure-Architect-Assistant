"""
Core engine for processing agent results and syncing checklist state.
"""

import json
import logging
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents_system.checklists.registry import ChecklistRegistry
from app.core.app_settings import AppSettings
from app.models.checklist import (
    Checklist,
    ChecklistItem,
    ChecklistItemEvaluation,
    ChecklistTemplate,
    EvaluationStatus,
)
from .normalize_helpers import (
    map_legacy_status,
)

logger = logging.getLogger(__name__)


class ChecklistEngine:
    """
    Core engine for processing agent results and syncing checklist state.

    Responsibilities:
    - Process agent AAA_STATE_UPDATE with checklist evaluations
    - Sync ProjectState.state ↔ normalized DB rows
    - Compute completion metrics and next actions
    - Support dual-write mode with consistency checks
    """

    def __init__(
        self,
        db_session_factory: Callable[[], AsyncSession],
        registry: ChecklistRegistry,
        settings: AppSettings,
    ) -> None:
        """
        Initialize the engine.

        Args:
            db_session_factory: Callable that returns an AsyncSession.
            registry: The template registry.
            settings: Application settings.
        """
        self.db_session_factory = db_session_factory
        self.registry = registry
        self.settings = settings
        self.namespace_uuid = UUID(settings.waf_namespace_uuid)
        self.chunk_size = settings.waf_sync_chunk_size
        self.feature_flag = settings.aaa_feature_waf_normalized

    async def process_agent_result(
        self,
        project_id: str,
        agent_result: dict,
    ) -> dict:
        """
        Process agent result containing AAA_STATE_UPDATE with checklist data.

        Args:
            project_id: Project ID
            agent_result: Agent output dict with potential AAA_STATE_UPDATE

        Returns:
            Merge summary dict with counts and status

        Raises:
            ValueError: If agent_result structure invalid
        """
        if not self.feature_flag:
            logger.debug(
                "WAF normalization feature disabled, skipping agent result processing"
            )
            return {"status": "skipped", "reason": "feature_disabled"}

        # Extract AAA_STATE_UPDATE
        state_update = agent_result.get("AAA_STATE_UPDATE", {})
        if not state_update:
            # Check if it's nested in metadata
            state_update = agent_result.get("metadata", {}).get("AAA_STATE_UPDATE", {})

        waf_checklist = state_update.get("wafChecklist", {})
        if not waf_checklist:
            return {"status": "skipped", "reason": "no_waf_data"}

        items_processed = 0
        evaluations_created = 0
        checklist_ids = []

        async with self.db_session_factory() as session:
            try:
                # Agent results can contain multiple templates/checklists
                # Format: { "template_slug": { "item_id": { "status": "...", "evidence": "..." } } }
                for template_slug, items_data in waf_checklist.items():
                    if template_slug in ["templates", "metadata"]:
                        continue

                    # 1. Get or create ChecklistTemplate
                    template_info = self.registry.get_template(template_slug)
                    if not template_info:
                        logger.warning(f"Template {template_slug} not found in registry")
                        continue

                    template_record = await self._get_or_create_template_record(
                        session, template_info
                    )

                    # 2. Get or create Checklist for project
                    checklist = await self._get_or_create_checklist(
                        session, project_id, template_record
                    )
                    checklist_ids.append(checklist.id)

                    # 3. Process items and evaluations
                    for item_slug, eval_data in items_data.items():
                        if not isinstance(eval_data, dict):
                            continue

                        # Find or create item definition
                        item = await self._get_or_create_item(
                            session, checklist, item_slug, template_info
                        )

                        # Create evaluation
                        raw_status = eval_data.get("status", "not_started")
                        status = map_legacy_status(raw_status)

                        evaluation = ChecklistItemEvaluation(
                            item_id=item.id,
                            project_id=project_id,
                            status=status,
                            evidence=eval_data.get("evidence", ""),
                            evaluator=agent_result.get("agent_name", "agent"),
                            source_type="agent_evaluation",
                        )
                        session.add(evaluation)

                        items_processed += 1
                        evaluations_created += 1

                await session.commit()
                return {
                    "status": "success",
                    "items_processed": items_processed,
                    "evaluations_created": evaluations_created,
                    "checklists": [str(cid) for cid in checklist_ids],
                }
            except Exception as e:
                await session.rollback()
                logger.error(
                    f"Failed to process agent result for project {project_id}: {e}"
                )
                raise

    async def sync_project_state_to_db(
        self,
        project_id: str,
        project_state: dict | str,
        chunk_size: int | None = None,
    ) -> dict:
        """
        Idempotent backfill of items and evaluations from ProjectState.
        """
        if isinstance(project_state, str):
            try:
                project_state = json.loads(project_state)
            except json.JSONDecodeError:
                return {"status": "error", "reason": "invalid_json"}

        waf_data = project_state.get("wafChecklist", {})
        if not waf_data:
            return {"status": "skipped", "reason": "no_waf_data"}

        chunk_size = chunk_size or self.chunk_size
        items_synced = 0
        evaluations_synced = 0
        errors = []

        # Handle both flat and nested structures (pillars as keys)
        checklists_to_process = []
        if "items" in waf_data:
            template_slug = waf_data.get("template", "azure-waf-v1")
            checklists_to_process.append((template_slug, waf_data))
        else:
            for k, v in waf_data.items():
                if isinstance(v, dict) and "items" in v:
                    checklists_to_process.append((k, v))

        if not checklists_to_process:
            return {"status": "skipped", "reason": "no_checklist_items_found"}

        async with self.db_session_factory() as session:
            try:
                for t_slug, c_data in checklists_to_process:
                    template_info = self.registry.get_template(t_slug)
                    if not template_info:
                        # Fallback to default if slug not found
                        template_info = self.registry.get_template("azure-waf-v1")
                    
                    if not template_info:
                        logger.warning(f"No template found for {t_slug}")
                        continue

                    template_record = await self._get_or_create_template_record(
                        session, template_info
                    )
                    checklist = await self._get_or_create_checklist(
                        session, project_id, template_record
                    )

                    # Extract items
                    legacy_items = c_data.get("items", [])
                    if isinstance(legacy_items, dict):
                        items_list = []
                        for k, v in legacy_items.items():
                            if isinstance(v, dict):
                                v["id"] = k
                                items_list.append(v)
                        legacy_items = items_list

                    if not isinstance(legacy_items, list):
                        continue

                    # Process in chunks
                    for i in range(0, len(legacy_items), chunk_size):
                        chunk = legacy_items[i : i + chunk_size]
                        for leg_item in chunk:
                            eval_count = await self._sync_legacy_item(
                                session, checklist, leg_item, template_info, project_id
                            )
                            evaluations_synced += eval_count
                            items_synced += 1

                await session.commit()
                return {
                    "status": "success",
                    "items_synced": items_synced,
                    "evaluations_synced": evaluations_synced,
                    "errors": errors,
                }
            except Exception as e:  # noqa: BLE001
                await session.rollback()
                logger.error(f"Failed to sync project state for {project_id}: {e}")
                return {"status": "error", "errors": [str(e)]}

    async def _sync_legacy_item(
        self,
        session: AsyncSession,
        checklist: Checklist,
        leg_item: dict,
        template_info: Any,
        project_id: str,
    ) -> int:
        """Helper to sync a single legacy item and its evaluations."""
        item_slug = leg_item.get("id") or leg_item.get("slug")
        if not item_slug:
            return 0

        item = await self._get_or_create_item(
            session, checklist, item_slug, template_info, legacy_title=leg_item.get("title")
        )

        # Process legacy evaluations
        leg_evals = leg_item.get("evaluations", [])
        if not leg_evals and "status" in leg_item:
            leg_evals = [
                {
                    "status": leg_item["status"],
                    "evidence": leg_item.get("evidence"),
                }
            ]

        eval_count = 0
        for leg_eval in leg_evals:
            status = map_legacy_status(leg_eval.get("status", "not_started"))
            evaluation = ChecklistItemEvaluation(
                item_id=item.id,
                project_id=project_id,
                status=status,
                evidence=leg_eval.get("evidence", ""),
                evaluator=leg_eval.get("evaluator", "legacy-migration"),
                source_type="legacy-migration",
                created_at=leg_eval.get("created_at") or datetime.now(timezone.utc),
            )
            session.add(evaluation)
            eval_count += 1

        return eval_count

    async def sync_db_to_project_state(self, project_id: str) -> dict:
        """
        Rebuild wafChecklist JSON from normalized rows.
        """
        async with self.db_session_factory() as session:
            stmt = (
                select(Checklist)
                .where(Checklist.project_id == project_id)
                .options(
                    selectinload(Checklist.items).selectinload(ChecklistItem.evaluations)
                )
            )
            result = await session.execute(stmt)
            checklists = result.scalars().all()

            waf_checklist = {}
            for checklist in checklists:
                checklist_data = {
                    "title": checklist.title,
                    "version": checklist.version,
                    "items": {},
                }
                for item in checklist.items:
                    # Get latest evaluation
                    latest_eval = None
                    if item.evaluations:
                        latest_eval = sorted(
                            item.evaluations, key=lambda x: x.created_at, reverse=True
                        )[0]

                    checklist_data["items"][item.template_item_id] = {
                        "title": item.title,
                        "status": latest_eval.status if latest_eval else "not_started",
                        "evidence": latest_eval.evidence if latest_eval else None,
                        "severity": item.severity,
                    }
                waf_checklist[checklist.template_slug] = checklist_data

            return waf_checklist

    async def evaluate_item(
        self, project_id: str, item_id: UUID, evaluation_payload: dict
    ) -> ChecklistItemEvaluation:
        """
        Create new evaluation for checklist item.
        """
        async with self.db_session_factory() as session:
            # Verify item belongs to project
            stmt = (
                select(ChecklistItem)
                .join(Checklist)
                .where(ChecklistItem.id == item_id)
                .where(Checklist.project_id == project_id)
            )
            result = await session.execute(stmt)
            item = result.scalar_one_or_none()
            if not item:
                raise ValueError(f"Item {item_id} not found for project {project_id}")

            status = evaluation_payload.get("status", EvaluationStatus.OPEN.value)

            evaluation = ChecklistItemEvaluation(
                item_id=item_id,
                project_id=project_id,
                status=status,
                comment=evaluation_payload.get("comment"),
                evidence=evaluation_payload.get("evidence"),
                evaluator=evaluation_payload.get("evaluator", "user"),
                source_type=evaluation_payload.get("source_type", "manual"),
            )
            session.add(evaluation)

            await session.commit()
            await session.refresh(evaluation)
            return evaluation

    async def list_next_actions(
        self, project_id: str, limit: int = 20, severity: str | None = None
    ) -> list[dict]:
        """
        List uncovered or incomplete checklist items prioritized by severity.
        """
        async with self.db_session_factory() as session:
            stmt = (
                select(ChecklistItem)
                .join(Checklist)
                .where(Checklist.project_id == project_id)
            )

            if severity:
                stmt = stmt.where(ChecklistItem.severity == severity)

            result = await session.execute(
                stmt.options(selectinload(ChecklistItem.evaluations))
            )
            items = result.scalars().all()

            # Manual filtering of latest status
            incomplete_items = []
            for item in items:
                latest_status = "not_started"
                last_eval_date = None
                if item.evaluations:
                    latest_eval = sorted(
                        item.evaluations, key=lambda x: x.created_at, reverse=True
                    )[0]
                    latest_status = latest_eval.status
                    last_eval_date = latest_eval.created_at

                if latest_status not in ["fixed", "fulfilled", "not_applicable"]:
                    incomplete_items.append(
                        {
                            "item_id": str(item.id),
                            "title": item.title,
                            "pillar": item.pillar,
                            "severity": item.severity,
                            "latest_status": latest_status,
                            "last_evaluated": last_eval_date.isoformat()
                            if last_eval_date
                            else None,
                        }
                    )

            # Sort by severity (critical > high > medium > low)
            sev_map = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            incomplete_items.sort(key=lambda x: sev_map.get(x["severity"], 4))

            return incomplete_items[:limit]

    async def compute_progress(
        self, project_id: str, checklist_id: UUID | None = None
    ) -> dict:
        """
        Calculate completion metrics for project or specific checklist.
        """
        async with self.db_session_factory() as session:
            stmt = (
                select(ChecklistItem)
                .join(Checklist)
                .where(Checklist.project_id == project_id)
            )
            if checklist_id:
                stmt = stmt.where(Checklist.id == checklist_id)

            result = await session.execute(
                stmt.options(selectinload(ChecklistItem.evaluations))
            )
            items = result.scalars().all()

            total_items = len(items)
            completed_count = 0
            severity_breakdown = {}

            for item in items:
                # Handle Enum or string
                sev = item.severity
                if hasattr(sev, "value"):
                    sev = sev.value
                sev = str(sev)

                if sev not in severity_breakdown:
                    severity_breakdown[sev] = {"total": 0, "completed": 0}
                severity_breakdown[sev]["total"] += 1

                latest_status = "not_started"
                if item.evaluations:
                    latest_eval = sorted(
                        item.evaluations, key=lambda x: x.created_at, reverse=True
                    )[0]
                    latest_status = latest_eval.status

                if latest_status in ["fixed", "fulfilled", "not_applicable"]:
                    completed_count += 1
                    severity_breakdown[sev]["completed"] += 1

            return {
                "total_items": total_items,
                "completed_items": completed_count,
                "percent_complete": (completed_count / total_items * 100)
                if total_items > 0
                else 0,
                "severity_breakdown": severity_breakdown,
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

    # Low-level helpers for ID stability and record management

    async def _get_or_create_template_record(
        self, session: AsyncSession, info: Any
    ) -> ChecklistTemplate:
        stmt = select(ChecklistTemplate).where(ChecklistTemplate.slug == info.slug)
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()
        if not record:
            record = ChecklistTemplate(
                slug=info.slug,
                title=info.title,
                description=getattr(info, "description", ""),
                version=info.version,
                source="microsoft-learn",
                source_url=getattr(info, "source_url", ""),
                source_version=info.version,
                content=getattr(info, "content", {}),
            )
            session.add(record)
            await session.flush()
        return record

    async def _get_or_create_checklist(
        self, session: AsyncSession, project_id: str, template: ChecklistTemplate
    ) -> Checklist:
        stmt = select(Checklist).where(
            and_(
                Checklist.project_id == project_id,
                Checklist.template_slug == template.slug,
            )
        )
        result = await session.execute(stmt)
        checklist = result.scalar_one_or_none()
        if not checklist:
            checklist = Checklist(
                project_id=project_id,
                template_id=template.id,
                template_slug=template.slug,
                title=template.title,
                version=template.version,
            )
            session.add(checklist)
            await session.flush()
        return checklist

    async def _get_or_create_item(
        self,
        session: AsyncSession,
        checklist: Checklist,
        slug: str,
        template_info: Any,
        legacy_title: str | None = None,
    ) -> ChecklistItem:
        # Use deterministic ID
        item_id = ChecklistItem.compute_deterministic_id(
            project_id=checklist.project_id,
            template_slug=checklist.template_slug or "general",
            template_item_id=slug,
            namespace_uuid=self.namespace_uuid,
        )

        item = await session.get(ChecklistItem, item_id)
        if not item:
            title = legacy_title or slug
            pillar = "General"
            severity = "medium"
            description = ""

            # Try to find metadata in template_info
            if hasattr(template_info, "items") and isinstance(template_info.items, list):
                for ti in template_info.items:
                    if ti.get("id") == slug or ti.get("slug") == slug:
                        title = ti.get("title", title)
                        pillar = ti.get("pillar", pillar)
                        severity = ti.get("priority", severity)
                        description = ti.get("description", "")
                        break

            item = ChecklistItem(
                id=item_id,
                checklist_id=checklist.id,
                template_item_id=slug,
                title=title,
                pillar=pillar,
                severity=severity,
                description=description,
            )
            session.add(item)
            await session.flush()
        return item
