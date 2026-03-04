"""Core checklist engine for legacy JSON <-> normalized table synchronization."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents_system.checklists.metrics import ChecklistMetricsService, severity_value
from app.agents_system.checklists.read_assembler import ChecklistReadAssembler
from app.agents_system.checklists.registry import ChecklistRegistry
from app.agents_system.checklists.state_parser import ChecklistStateParser
from app.agents_system.checklists.sync_writer import ChecklistSyncWriter
from app.agents_system.checklists.template_resolver import ChecklistTemplateResolver
from app.core.app_settings import AppSettings
from app.models.checklist import (
    Checklist,
    ChecklistItem,
    ChecklistItemEvaluation,
    ChecklistTemplate,
    EvaluationStatus,
    SeverityLevel,
)

logger = logging.getLogger(__name__)


class _SessionFactory(Protocol):
    """Callable that returns an async context manager yielding an AsyncSession."""

    @asynccontextmanager
    async def __call__(self) -> AsyncIterator[AsyncSession]: ...  # pragma: no cover


_FINAL_STATUSES = {EvaluationStatus.FIXED, EvaluationStatus.FALSE_POSITIVE}
_SEVERITY_ORDER = {
    SeverityLevel.CRITICAL.value: 0,
    SeverityLevel.HIGH.value: 1,
    SeverityLevel.MEDIUM.value: 2,
    SeverityLevel.LOW.value: 3,
}


class ChecklistEngine:
    """Engine for WAF checklist synchronization and evaluation management."""

    def __init__(
        self,
        db_session_factory: _SessionFactory,
        registry: ChecklistRegistry,
        settings: AppSettings,
    ) -> None:
        self.db_session_factory = db_session_factory
        self.registry = registry
        self.settings = settings
        self.namespace_uuid = UUID(str(settings.waf_namespace_uuid))
        self.chunk_size = int(settings.waf_sync_chunk_size)
        self.feature_flag = bool(settings.aaa_feature_waf_normalized)

        self._parser = ChecklistStateParser()
        self._resolver = ChecklistTemplateResolver(registry)
        self._writer = ChecklistSyncWriter(self._resolver, self.namespace_uuid)
        self._assembler = ChecklistReadAssembler(self._resolver)
        self._metrics = ChecklistMetricsService()

    @staticmethod
    def _extract_state_update(agent_result: dict[str, Any]) -> dict[str, Any] | None:
        state_update = agent_result.get("AAA_STATE_UPDATE")
        if isinstance(state_update, dict):
            return state_update
        metadata = agent_result.get("metadata")
        if isinstance(metadata, dict):
            return metadata.get("AAA_STATE_UPDATE") if isinstance(metadata.get("AAA_STATE_UPDATE"), dict) else None
        return None

    async def process_agent_result(self, project_id: str, agent_result: dict[str, Any]) -> dict[str, Any]:
        """Process an agent output payload and sync WAF updates to normalized tables."""
        if not self.feature_flag:
            return {"status": "skipped", "reason": "feature_disabled"}

        state_update = self._extract_state_update(agent_result)
        if state_update is None:
            return {"status": "skipped", "reason": "no_state_update"}

        waf_checklist = state_update.get("wafChecklist")
        if not isinstance(waf_checklist, dict):
            return {"status": "skipped", "reason": "no_waf_data"}

        summary = await self.sync_project_state_to_db(
            project_id=project_id,
            project_state={"wafChecklist": waf_checklist},
        )
        if summary.get("status") != "success":
            return summary

        return {
            "status": "success",
            "items_processed": summary.get("items_synced", 0),
            "evaluations_created": summary.get("evaluations_synced", 0),
            "checklists": summary.get("checklists", []),
        }

    async def sync_project_state_to_db(
        self,
        project_id: str,
        project_state: dict[str, Any] | str,
        chunk_size: int | None = None,
    ) -> dict[str, Any]:
        """Idempotently sync legacy ``wafChecklist`` JSON into normalized rows."""
        parsed_state = self._parser.parse_project_state(project_state)
        if parsed_state is None:
            return {"status": "error", "reason": "invalid_json"}

        waf_data = parsed_state.get("wafChecklist")
        if not isinstance(waf_data, dict):
            return {"status": "skipped", "reason": "no_waf_data"}

        checklists_to_process = self._parser.extract_checklists_from_waf_data(waf_data)
        if not checklists_to_process:
            return {"status": "skipped", "reason": "no_checklist_items_found"}

        return await self._sync_checklists(
            project_id,
            checklists_to_process,
            int(chunk_size or self.chunk_size),
        )

    async def _sync_single_checklist(
        self,
        session: AsyncSession,
        project_id: str,
        template_slug: str,
        checklist_payload: dict[str, Any],
        effective_chunk_size: int,
    ) -> tuple[int, int, str | None]:
        """Sync one checklist payload. Returns (items_synced, evals_synced, checklist_id_or_None)."""
        resolved_template = self._resolver.resolve_template(template_slug, checklist_payload)
        if resolved_template is None:
            return 0, 0, None

        template_record = await self._writer.get_or_create_template_record(session, resolved_template)
        checklist = await self._writer.get_or_create_checklist(session, project_id, template_record)

        legacy_items = self._parser.normalize_items_container(checklist_payload.get("items", []))
        items_synced = 0
        evaluations_synced = 0

        for start in range(0, len(legacy_items), effective_chunk_size):
            chunk = legacy_items[start : start + effective_chunk_size]
            for legacy_item in chunk:
                evaluations_added = await self._writer.sync_legacy_item(
                    session=session,
                    checklist=checklist,
                    legacy_item=legacy_item,
                    template=resolved_template,
                    project_id=project_id,
                )
                items_synced += 1
                evaluations_synced += evaluations_added
            await session.flush()

        return items_synced, evaluations_synced, str(checklist.id)

    async def _sync_checklists(
        self,
        project_id: str,
        checklists_to_process: list[tuple[str, dict[str, Any]]],
        effective_chunk_size: int,
    ) -> dict[str, Any]:
        items_synced = 0
        evaluations_synced = 0
        checklist_ids: list[str] = []
        errors: list[str] = []

        async with self.db_session_factory() as session:
            try:
                for template_slug, checklist_payload in checklists_to_process:
                    count_items, count_evals, checklist_id = await self._sync_single_checklist(
                        session=session,
                        project_id=project_id,
                        template_slug=template_slug,
                        checklist_payload=checklist_payload,
                        effective_chunk_size=effective_chunk_size,
                    )
                    if checklist_id is None:
                        errors.append(f"template_not_found:{template_slug}")
                        continue
                    items_synced += count_items
                    evaluations_synced += count_evals
                    checklist_ids.append(checklist_id)

                await session.commit()
            except Exception as exc:
                await session.rollback()
                logger.error("Failed to sync project state for %s: %s", project_id, exc, exc_info=True)
                return {"status": "error", "errors": [str(exc)]}

        return {
            "status": "success",
            "items_synced": items_synced,
            "evaluations_synced": evaluations_synced,
            "checklists": checklist_ids,
            "errors": errors,
        }

    async def sync_db_to_project_state(self, project_id: str) -> dict[str, Any]:
        """Reconstruct legacy ``wafChecklist`` map from normalized rows."""
        async with self.db_session_factory() as session:
            result = await session.execute(
                select(Checklist)
                .where(Checklist.project_id == project_id)
                .options(selectinload(Checklist.items).selectinload(ChecklistItem.evaluations))
            )
            checklists = result.scalars().all()

        if not checklists:
            return self._assembler.build_empty_reconstructed_state()
        return self._assembler.reconstruct_from_checklists(checklists)

    async def evaluate_item(
        self,
        project_id: str,
        item_id: UUID,
        evaluation_payload: dict[str, Any],
    ) -> ChecklistItemEvaluation:
        """Create a manual evaluation for a checklist item."""
        async with self.db_session_factory() as session:
            item = (
                await session.execute(
                    select(ChecklistItem)
                    .join(Checklist)
                    .where(ChecklistItem.id == item_id)
                    .where(Checklist.project_id == project_id)
                )
            ).scalar_one_or_none()
            if item is None:
                raise ValueError(f"Item {item_id} not found for project {project_id}")

            normalized_status = ChecklistSyncWriter._normalize_evaluation_status(
                evaluation_payload.get("status", EvaluationStatus.OPEN.value)
            )

            evaluation = ChecklistItemEvaluation(
                item_id=item_id,
                project_id=project_id,
                status=normalized_status,
                comment=evaluation_payload.get("comment"),
                evidence=evaluation_payload.get("evidence"),
                evaluator=str(evaluation_payload.get("evaluator", "user")),
                source_type=str(evaluation_payload.get("source_type", "manual")),
            )
            session.add(evaluation)

            await session.commit()
            await session.refresh(evaluation)
            return evaluation

    async def list_next_actions(
        self,
        project_id: str,
        limit: int = 20,
        severity: str | None = None,
    ) -> list[dict[str, Any]]:
        """List incomplete checklist items prioritized by severity."""
        async with self.db_session_factory() as session:
            stmt = select(ChecklistItem).join(Checklist).where(Checklist.project_id == project_id)
            if severity:
                normalized_severity = ChecklistSyncWriter._normalize_severity(severity)
                stmt = stmt.where(ChecklistItem.severity == normalized_severity)
            result = await session.execute(stmt.options(selectinload(ChecklistItem.evaluations)))
            items = result.scalars().all()

        pending: list[dict[str, Any]] = []
        for item in items:
            latest_status = self._metrics.latest_status(item.evaluations)
            if latest_status in _FINAL_STATUSES:
                continue
            pending.append(
                {
                    "item_id": str(item.id),
                    "template_item_id": item.template_item_id,
                    "title": item.title,
                    "pillar": item.pillar,
                    "severity": severity_value(item.severity),
                    "latest_status": latest_status.value,
                    "last_evaluated": self._metrics.latest_timestamp(item.evaluations),
                }
            )

        pending.sort(key=lambda i: _SEVERITY_ORDER.get(str(i["severity"]), 99))
        return pending[:limit]

    async def compute_progress(self, project_id: str, checklist_id: UUID | None = None) -> dict[str, Any]:
        """Compute progress metrics for a project (or a specific checklist)."""
        async with self.db_session_factory() as session:
            stmt = select(ChecklistItem).join(Checklist).where(Checklist.project_id == project_id)
            if checklist_id:
                stmt = stmt.where(Checklist.id == checklist_id)

            result = await session.execute(stmt.options(selectinload(ChecklistItem.evaluations)))
            items = result.scalars().all()

        total_items = len(items)
        completed_items = 0
        severity_breakdown: dict[str, dict[str, int]] = {}
        status_breakdown: dict[str, int] = {}

        for item in items:
            severity_key = severity_value(item.severity)
            severity_entry = severity_breakdown.setdefault(severity_key, {"total": 0, "completed": 0})
            severity_entry["total"] += 1

            latest_status = self._metrics.latest_status(item.evaluations)
            latest_status_value = latest_status.value
            status_breakdown[latest_status_value] = status_breakdown.get(latest_status_value, 0) + 1
            if latest_status in _FINAL_STATUSES:
                completed_items += 1
                severity_entry["completed"] += 1

        percent_complete = (completed_items / total_items * 100) if total_items else 0.0
        return {
            "total_items": total_items,
            "completed_items": completed_items,
            "percent_complete": percent_complete,
            "severity_breakdown": severity_breakdown,
            "status_breakdown": status_breakdown,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    async def ensure_project_checklist(
        self,
        project_id: str,
        template_slug: str = "azure-waf-v1",
    ) -> Checklist | None:
        """Ensure a project has at least one checklist instantiated from a template."""
        checklists = await self.ensure_project_checklists(project_id, [template_slug])
        return checklists[0] if checklists else None

    async def ensure_project_checklists(
        self,
        project_id: str,
        template_slugs: list[str] | None = None,
    ) -> list[Checklist]:
        """Ensure one checklist exists per requested template slug."""
        selected_slugs = self._resolver.select_bootstrap_template_slugs(template_slugs)
        if not selected_slugs:
            logger.warning("Cannot bootstrap checklists for %s: no templates available", project_id)
            return []

        created: list[Checklist] = []
        async with self.db_session_factory() as session:
            try:
                for slug in selected_slugs:
                    template = self.registry.get_template(slug)
                    if template is None:
                        continue

                    template_record = await self._writer.get_or_create_template_record(session, template)
                    checklist = await self._writer.get_or_create_checklist(session, project_id, template_record)

                    for template_item in self._resolver.collect_template_items(template):
                        template_item_id = str(template_item.get("id") or template_item.get("slug") or "").strip()
                        if not template_item_id:
                            continue
                        await self._writer.get_or_create_item(
                            session=session,
                            checklist=checklist,
                            template_item_id=template_item_id,
                            template=template,
                            legacy_item=template_item,
                        )
                    created.append(checklist)

                await session.commit()
                return created
            except Exception:
                await session.rollback()
                logger.exception("Failed to bootstrap checklists for project %s", project_id)
                raise

    # Compatibility helpers retained for existing callers/tests.
    def default_template_slug(self) -> str:
        return self._resolver.default_template_slug()

    def _select_bootstrap_template_slugs(self, requested: list[str] | None) -> list[str]:
        return self._resolver.select_bootstrap_template_slugs(requested)

    def _extract_known_pillars(self, template: ChecklistTemplate | None) -> list[str]:
        return self._resolver.extract_known_pillars(template)
