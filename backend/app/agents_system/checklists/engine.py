"""Core checklist engine for legacy JSON <-> normalized table synchronization."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents_system.checklists.registry import ChecklistRegistry
from app.agents_system.checklists.default_templates import resolve_bootstrap_template_slugs
from app.core.app_settings import AppSettings
from app.models.checklist import (
    Checklist,
    ChecklistItem,
    ChecklistItemEvaluation,
    ChecklistTemplate,
    EvaluationStatus,
    SeverityLevel,
)
from .normalize_helpers import map_legacy_status, reconstruct_legacy_waf_json

logger = logging.getLogger(__name__)


_FINAL_STATUSES = {EvaluationStatus.FIXED.value, EvaluationStatus.FALSE_POSITIVE.value}
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
        db_session_factory: Any,
        registry: ChecklistRegistry,
        settings: AppSettings,
    ) -> None:
        self.db_session_factory = db_session_factory
        self.registry = registry
        self.settings = settings
        self.namespace_uuid = UUID(str(settings.waf_namespace_uuid))
        self.chunk_size = int(settings.waf_sync_chunk_size)
        self.feature_flag = bool(settings.aaa_feature_waf_normalized)

    async def process_agent_result(self, project_id: str, agent_result: dict[str, Any]) -> dict[str, Any]:
        """Process an agent output payload and sync WAF updates to normalized tables."""
        if not self.feature_flag:
            return {"status": "skipped", "reason": "feature_disabled"}

        state_update = agent_result.get("AAA_STATE_UPDATE")
        if not isinstance(state_update, dict):
            metadata = agent_result.get("metadata")
            if isinstance(metadata, dict):
                state_update = metadata.get("AAA_STATE_UPDATE")
        if not isinstance(state_update, dict):
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
        if isinstance(project_state, str):
            try:
                parsed_state = json.loads(project_state)
            except json.JSONDecodeError:
                return {"status": "error", "reason": "invalid_json"}
        else:
            parsed_state = project_state

        waf_data = parsed_state.get("wafChecklist")
        if not isinstance(waf_data, dict):
            return {"status": "skipped", "reason": "no_waf_data"}

        checklists_to_process = self._extract_checklists_from_waf_data(waf_data)
        if not checklists_to_process:
            return {"status": "skipped", "reason": "no_checklist_items_found"}

        effective_chunk_size = int(chunk_size or self.chunk_size)
        items_synced = 0
        evaluations_synced = 0
        checklist_ids: list[str] = []
        errors: list[str] = []

        async with self.db_session_factory() as session:
            try:
                for template_slug, checklist_payload in checklists_to_process:
                    template_info = self._resolve_template(template_slug, checklist_payload)
                    if template_info is None:
                        errors.append(f"template_not_found:{template_slug}")
                        continue

                    template_record = await self._get_or_create_template_record(session, template_info)
                    checklist = await self._get_or_create_checklist(session, project_id, template_record)
                    checklist_ids.append(str(checklist.id))

                    legacy_items = self._normalize_items_container(checklist_payload.get("items", []))
                    if not legacy_items:
                        continue

                    for start in range(0, len(legacy_items), effective_chunk_size):
                        chunk = legacy_items[start : start + effective_chunk_size]
                        for legacy_item in chunk:
                            evaluations_added = await self._sync_legacy_item(
                                session=session,
                                checklist=checklist,
                                legacy_item=legacy_item,
                                template_info=template_info,
                                project_id=project_id,
                            )
                            items_synced += 1
                            evaluations_synced += evaluations_added

                await session.commit()
            except Exception as exc:  # noqa: BLE001
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
                templates = self.registry.list_templates()
                selected_slugs = resolve_bootstrap_template_slugs(
                    getattr(template, "slug", "") for template in templates
                )
                if not selected_slugs and templates:
                    selected_slugs = [getattr(templates[0], "slug", "")]

                reconstructed_empty: dict[str, Any] = {}
                for slug in selected_slugs:
                    if not slug:
                        continue
                    template_info = self.registry.get_template(slug)
                    if template_info is None:
                        continue

                    known_pillars = self._extract_known_pillars(template_info)
                    reconstructed_empty[slug] = reconstruct_legacy_waf_json(
                        template_slug=slug,
                        version=getattr(template_info, "version", "1"),
                        items_with_evals=[],
                        known_pillars=known_pillars,
                    )
                if reconstructed_empty:
                    return reconstructed_empty
                if not templates:
                    return {}
                return {}

            reconstructed: dict[str, Any] = {}
            for checklist in checklists:
                template_slug = checklist.template_slug or self.default_template_slug()
                template_info = self.registry.get_template(template_slug)
                known_pillars = self._extract_known_pillars(template_info) if template_info else None
                reconstructed[template_slug] = reconstruct_legacy_waf_json(
                    template_slug=template_slug,
                    version=checklist.version,
                    items_with_evals=list(checklist.items),
                    known_pillars=known_pillars,
                )
                reconstructed[template_slug]["title"] = checklist.title
            return reconstructed

    async def evaluate_item(
        self, project_id: str, item_id: UUID, evaluation_payload: dict[str, Any]
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

            raw_status = str(evaluation_payload.get("status", EvaluationStatus.OPEN.value))
            normalized_status = map_legacy_status(raw_status)

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
        self, project_id: str, limit: int = 20, severity: str | None = None
    ) -> list[dict[str, Any]]:
        """List incomplete checklist items prioritized by severity."""
        async with self.db_session_factory() as session:
            stmt = select(ChecklistItem).join(Checklist).where(Checklist.project_id == project_id)
            if severity:
                stmt = stmt.where(ChecklistItem.severity == severity)
            result = await session.execute(stmt.options(selectinload(ChecklistItem.evaluations)))
            items = result.scalars().all()

            pending: list[dict[str, Any]] = []
            for item in items:
                latest_status = self._latest_status(item.evaluations)
                if latest_status in _FINAL_STATUSES:
                    continue
                pending.append(
                    {
                        "item_id": str(item.id),
                        "template_item_id": item.template_item_id,
                        "title": item.title,
                        "pillar": item.pillar,
                        "severity": item.severity.value if hasattr(item.severity, "value") else str(item.severity),
                        "latest_status": latest_status,
                        "last_evaluated": self._latest_timestamp(item.evaluations),
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
                severity = item.severity.value if hasattr(item.severity, "value") else str(item.severity)
                severity_entry = severity_breakdown.setdefault(severity, {"total": 0, "completed": 0})
                severity_entry["total"] += 1

                latest_status = self._latest_status(item.evaluations)
                status_breakdown[latest_status] = status_breakdown.get(latest_status, 0) + 1
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
        self, project_id: str, template_slug: str = "azure-waf-v1"
    ) -> Checklist | None:
        """
        Ensure a project has at least one checklist instantiated from a template.

        This is used to guarantee UX visibility for existing projects even before
        any WAF evaluations are recorded.
        """
        checklists = await self.ensure_project_checklists(project_id, [template_slug])
        return checklists[0] if checklists else None

    async def ensure_project_checklists(
        self, project_id: str, template_slugs: list[str] | None = None
    ) -> list[Checklist]:
        """Ensure one checklist exists per requested template slug."""
        selected_slugs = self._select_bootstrap_template_slugs(template_slugs)
        if not selected_slugs:
            logger.warning("Cannot bootstrap checklists for %s: no templates available", project_id)
            return []

        created: list[Checklist] = []
        async with self.db_session_factory() as session:
            try:
                for slug in selected_slugs:
                    template_info = self.registry.get_template(slug)
                    if template_info is None:
                        continue

                    template_record = await self._get_or_create_template_record(session, template_info)
                    checklist = await self._get_or_create_checklist(session, project_id, template_record)

                    for template_item in self._collect_template_items(template_info):
                        template_item_id = str(
                            template_item.get("id") or template_item.get("slug") or ""
                        ).strip()
                        if not template_item_id:
                            continue
                        await self._get_or_create_item(
                            session=session,
                            checklist=checklist,
                            template_item_id=template_item_id,
                            template_info=template_info,
                            legacy_item=template_item,
                        )
                    created.append(checklist)

                await session.commit()
                return created
            except Exception as exc:  # noqa: BLE001
                await session.rollback()
                logger.error(
                    "Failed to bootstrap checklists for project %s: %s",
                    project_id,
                    exc,
                    exc_info=True,
                )
                raise

    async def _get_or_create_template_record(self, session: AsyncSession, info: Any) -> ChecklistTemplate:
        existing = (
            await session.execute(select(ChecklistTemplate).where(ChecklistTemplate.slug == info.slug))
        ).scalar_one_or_none()
        if existing:
            return existing

        record = ChecklistTemplate(
            slug=info.slug,
            title=info.title,
            description=getattr(info, "description", None),
            version=info.version,
            source=getattr(info, "source", "microsoft-learn"),
            source_url=getattr(info, "source_url", ""),
            source_version=getattr(info, "source_version", info.version),
            content=getattr(info, "content", {}) or {},
        )
        session.add(record)
        await session.flush()
        return record

    async def _get_or_create_checklist(
        self, session: AsyncSession, project_id: str, template: ChecklistTemplate
    ) -> Checklist:
        existing = (
            await session.execute(
                select(Checklist).where(
                    and_(Checklist.project_id == project_id, Checklist.template_slug == template.slug)
                )
            )
        ).scalar_one_or_none()
        if existing:
            return existing

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
        template_item_id: str,
        template_info: Any,
        legacy_item: dict[str, Any] | None = None,
    ) -> ChecklistItem:
        deterministic_id = ChecklistItem.compute_deterministic_id(
            project_id=checklist.project_id,
            template_slug=checklist.template_slug or "general",
            template_item_id=template_item_id,
            namespace_uuid=self.namespace_uuid,
        )
        item = await session.get(ChecklistItem, deterministic_id)
        if item:
            return item

        metadata = self._resolve_template_item_metadata(template_info, template_item_id)
        title = str(metadata.get("title") or (legacy_item or {}).get("topic") or (legacy_item or {}).get("title") or template_item_id)
        pillar = str(metadata.get("pillar") or (legacy_item or {}).get("pillar") or "General")
        description = str(metadata.get("description") or "")
        severity = self._normalize_severity(
            metadata.get("severity") or metadata.get("priority") or (legacy_item or {}).get("severity")
        )

        item = ChecklistItem(
            id=deterministic_id,
            checklist_id=checklist.id,
            template_item_id=template_item_id,
            title=title,
            description=description,
            pillar=pillar,
            severity=severity,
            guidance=metadata.get("guidance"),
            item_metadata=metadata if metadata else None,
        )
        session.add(item)
        await session.flush()
        return item

    async def _sync_legacy_item(
        self,
        session: AsyncSession,
        checklist: Checklist,
        legacy_item: dict[str, Any],
        template_info: Any,
        project_id: str,
    ) -> int:
        item_slug = str(legacy_item.get("id") or legacy_item.get("slug") or "").strip()
        if not item_slug:
            return 0

        item = await self._get_or_create_item(
            session=session,
            checklist=checklist,
            template_item_id=item_slug,
            template_info=template_info,
            legacy_item=legacy_item,
        )

        legacy_evals = legacy_item.get("evaluations", [])
        if not isinstance(legacy_evals, list) or not legacy_evals:
            if "status" in legacy_item:
                legacy_evals = [
                    {
                        "status": legacy_item.get("status"),
                        "evidence": legacy_item.get("evidence"),
                    }
                ]
            else:
                return 0

        created_count = 0
        for raw_eval in legacy_evals:
            if not isinstance(raw_eval, dict):
                continue
            normalized_status = map_legacy_status(str(raw_eval.get("status", "open")))
            evidence_value = raw_eval.get("evidence", "")
            evaluator = str(raw_eval.get("evaluator", "legacy-migration"))
            source_id = raw_eval.get("id")
            source_id_str = str(source_id) if source_id else None

            if await self._evaluation_exists(
                session=session,
                item_id=item.id,
                source_type="legacy-migration",
                source_id=source_id_str,
                status=normalized_status,
                evidence=evidence_value,
            ):
                continue

            evaluation = ChecklistItemEvaluation(
                item_id=item.id,
                project_id=project_id,
                status=normalized_status,
                evidence=evidence_value,
                evaluator=evaluator,
                source_type="legacy-migration",
                source_id=source_id_str,
            )
            session.add(evaluation)
            created_count += 1

        return created_count

    async def _evaluation_exists(
        self,
        session: AsyncSession,
        item_id: UUID,
        source_type: str,
        source_id: str | None,
        status: str,
        evidence: Any,
    ) -> bool:
        stmt = select(ChecklistItemEvaluation).where(
            ChecklistItemEvaluation.item_id == item_id,
            ChecklistItemEvaluation.source_type == source_type,
        )
        if source_id:
            stmt = stmt.where(ChecklistItemEvaluation.source_id == source_id)
        existing = (await session.execute(stmt)).scalars().all()
        if not existing:
            return False

        for entry in existing:
            entry_status = entry.status.value if hasattr(entry.status, "value") else str(entry.status)
            if entry_status != status:
                continue
            if entry.evidence == evidence:
                return True
        return False

    def _extract_checklists_from_waf_data(self, waf_data: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
        if "items" in waf_data:
            template_slug = self._resolve_template_slug(waf_data)
            return [(template_slug, waf_data)]

        checklists: list[tuple[str, dict[str, Any]]] = []
        for key, value in waf_data.items():
            if key in {"templates", "metadata"}:
                continue
            if isinstance(value, dict) and "items" in value:
                checklists.append((key, value))
        return checklists

    def _resolve_template_slug(self, payload: dict[str, Any]) -> str:
        explicit = payload.get("template")
        if isinstance(explicit, str) and explicit.strip():
            return explicit.strip()

        templates = payload.get("templates")
        if isinstance(templates, list):
            for template in templates:
                if isinstance(template, dict):
                    slug = template.get("slug")
                    if isinstance(slug, str) and slug.strip():
                        return slug.strip()
        return self.default_template_slug()

    def _resolve_template(self, template_slug: str, payload: dict[str, Any]) -> Any | None:
        template = self.registry.get_template(template_slug)
        if template:
            return template

        templates = payload.get("templates")
        if isinstance(templates, list):
            for candidate in templates:
                if not isinstance(candidate, dict):
                    continue
                slug = str(candidate.get("slug", "")).strip()
                if slug == template_slug:
                    temp = self.registry.get_template(slug)
                    if temp:
                        return temp
        fallback = self.registry.get_template(self.default_template_slug())
        if fallback is None:
            logger.warning("No checklist template found for '%s' and no fallback template available", template_slug)
        return fallback

    def default_template_slug(self) -> str:
        """Resolve the best default template slug from available registry templates."""
        available = [template.slug for template in self.registry.list_templates()]
        selected = resolve_bootstrap_template_slugs(available)
        if selected:
            return selected[0]
        return available[0] if available else "azure-waf-v1"

    def _select_bootstrap_template_slugs(self, requested: list[str] | None) -> list[str]:
        available = [template.slug for template in self.registry.list_templates()]
        if requested:
            available_set = set(available)
            selected = [slug for slug in requested if slug in available_set]
            if selected:
                return selected
        return resolve_bootstrap_template_slugs(available)

    def _normalize_items_container(self, legacy_items: Any) -> list[dict[str, Any]]:
        if isinstance(legacy_items, list):
            return [item for item in legacy_items if isinstance(item, dict)]
        if isinstance(legacy_items, dict):
            items: list[dict[str, Any]] = []
            for key, value in legacy_items.items():
                if not isinstance(value, dict):
                    continue
                merged = dict(value)
                merged.setdefault("id", key)
                items.append(merged)
            return items
        return []

    def _resolve_template_item_metadata(self, template_info: Any, template_item_id: str) -> dict[str, Any]:
        candidates = []
        content = getattr(template_info, "content", None)
        if isinstance(content, dict):
            content_items = content.get("items")
            if isinstance(content_items, list):
                candidates.extend(item for item in content_items if isinstance(item, dict))

        raw_items = getattr(template_info, "items", None)
        if isinstance(raw_items, list):
            candidates.extend(item for item in raw_items if isinstance(item, dict))

        for candidate in candidates:
            candidate_id = str(candidate.get("id") or candidate.get("slug") or "").strip()
            if candidate_id == template_item_id:
                return candidate
        return {}

    def _collect_template_items(self, template_info: Any) -> list[dict[str, Any]]:
        """Collect unique template item definitions from known template shapes."""
        raw_items: list[dict[str, Any]] = []
        content = getattr(template_info, "content", None)
        if isinstance(content, dict):
            content_items = content.get("items")
            if isinstance(content_items, list):
                raw_items.extend(i for i in content_items if isinstance(i, dict))

        template_items = getattr(template_info, "items", None)
        if isinstance(template_items, list):
            raw_items.extend(i for i in template_items if isinstance(i, dict))

        deduped: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in raw_items:
            item_id = str(item.get("id") or item.get("slug") or "").strip()
            if not item_id or item_id in seen:
                continue
            seen.add(item_id)
            deduped.append(item)
        return deduped

    def _extract_known_pillars(self, template_info: Any | None) -> list[str]:
        if template_info is None:
            return []
        content = getattr(template_info, "content", None)
        if not isinstance(content, dict):
            return []
        items = content.get("items")
        if not isinstance(items, list):
            return []
        return sorted({str(i.get("pillar")).strip() for i in items if isinstance(i, dict) and i.get("pillar")})

    def _normalize_severity(self, raw_severity: Any) -> str:
        value = str(raw_severity or SeverityLevel.MEDIUM.value).strip().lower()
        if value in {SeverityLevel.LOW.value, SeverityLevel.MEDIUM.value, SeverityLevel.HIGH.value, SeverityLevel.CRITICAL.value}:
            return value
        return SeverityLevel.MEDIUM.value

    def _latest_status(self, evaluations: list[ChecklistItemEvaluation]) -> str:
        if not evaluations:
            return EvaluationStatus.OPEN.value
        latest = max(evaluations, key=lambda e: e.created_at or datetime.min.replace(tzinfo=timezone.utc))
        return latest.status.value if hasattr(latest.status, "value") else str(latest.status)

    def _latest_timestamp(self, evaluations: list[ChecklistItemEvaluation]) -> str | None:
        if not evaluations:
            return None
        latest = max(evaluations, key=lambda e: e.created_at or datetime.min.replace(tzinfo=timezone.utc))
        return latest.created_at.isoformat() if latest.created_at else None
