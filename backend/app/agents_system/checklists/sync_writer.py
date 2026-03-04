"""Persistence helpers for checklist synchronization."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents_system.checklists.normalize_helpers import map_legacy_status
from app.agents_system.checklists.template_resolver import ChecklistTemplateResolver
from app.models.checklist import (
    Checklist,
    ChecklistItem,
    ChecklistItemEvaluation,
    ChecklistTemplate,
    EvaluationStatus,
    SeverityLevel,
)

_T = TypeVar("_T")


def status_value(value: EvaluationStatus | str) -> str:
    return value.value if isinstance(value, EvaluationStatus) else str(value)


class ChecklistSyncWriter:
    """Persistence helper for templates/checklists/items/evaluations."""

    def __init__(self, resolver: ChecklistTemplateResolver, namespace_uuid: UUID) -> None:
        self.resolver = resolver
        self.namespace_uuid = namespace_uuid

    async def _get_or_create(
        self,
        session: AsyncSession,
        new_record: _T,
        fetch: Callable[[], Awaitable[_T | None]],
    ) -> _T:
        """Insert `new_record` idempotently: on IntegrityError, re-fetch and return the winner."""
        existing = await fetch()
        if existing is not None:
            return existing
        savepoint = await session.begin_nested()
        try:
            session.add(new_record)
            await session.flush()
            await savepoint.commit()
            return new_record
        except IntegrityError:
            await savepoint.rollback()
            existing_after = await fetch()
            if existing_after is None:
                raise
            return existing_after

    async def get_or_create_template_record(
        self,
        session: AsyncSession,
        template: ChecklistTemplate,
    ) -> ChecklistTemplate:
        record = ChecklistTemplate(
            slug=template.slug,
            title=template.title,
            description=getattr(template, "description", None),
            version=template.version,
            source=getattr(template, "source", "microsoft-learn"),
            source_url=getattr(template, "source_url", ""),
            source_version=getattr(template, "source_version", template.version),
            content=getattr(template, "content", {}) or {},
        )

        async def fetch() -> ChecklistTemplate | None:
            return (
                await session.execute(select(ChecklistTemplate).where(ChecklistTemplate.slug == template.slug))
            ).scalar_one_or_none()

        return await self._get_or_create(session, record, fetch)

    async def get_or_create_checklist(
        self,
        session: AsyncSession,
        project_id: str,
        template: ChecklistTemplate,
    ) -> Checklist:
        checklist = Checklist(
            project_id=project_id,
            template_id=template.id,
            template_slug=template.slug,
            title=template.title,
            version=template.version,
        )

        async def fetch() -> Checklist | None:
            return (
                await session.execute(
                    select(Checklist).where(
                        and_(Checklist.project_id == project_id, Checklist.template_slug == template.slug)
                    )
                )
            ).scalar_one_or_none()

        return await self._get_or_create(session, checklist, fetch)

    async def get_or_create_item(
        self,
        session: AsyncSession,
        checklist: Checklist,
        template_item_id: str,
        template: ChecklistTemplate,
        legacy_item: dict[str, Any] | None = None,
    ) -> ChecklistItem:
        deterministic_id = ChecklistItem.compute_deterministic_id(
            project_id=checklist.project_id,
            template_slug=checklist.template_slug or "general",
            template_item_id=template_item_id,
            namespace_uuid=self.namespace_uuid,
        )

        async def fetch() -> ChecklistItem | None:
            return await session.get(ChecklistItem, deterministic_id)

        metadata = self.resolver.metadata_for_item(template, template_item_id)
        legacy = legacy_item or {}
        title = str(metadata.get("title") or legacy.get("topic") or legacy.get("title") or template_item_id)
        pillar = str(metadata.get("pillar") or legacy.get("pillar") or "General")
        description = str(metadata.get("description") or "")
        severity = self._normalize_severity(
            metadata.get("severity") or metadata.get("priority") or legacy.get("severity")
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

        return await self._get_or_create(session, item, fetch)

    async def sync_legacy_item(
        self,
        session: AsyncSession,
        checklist: Checklist,
        legacy_item: dict[str, Any],
        template: ChecklistTemplate,
        project_id: str,
    ) -> int:
        item_slug = str(legacy_item.get("id") or legacy_item.get("slug") or "").strip()
        if not item_slug:
            return 0

        item = await self.get_or_create_item(
            session=session,
            checklist=checklist,
            template_item_id=item_slug,
            template=template,
            legacy_item=legacy_item,
        )

        legacy_evals = self._extract_legacy_evals(legacy_item)
        if not legacy_evals:
            return 0

        existing_fingerprints = await self._existing_eval_fingerprints(session, item.id)
        created_count = sum(
            self._create_evaluation(session, item, project_id, raw_eval, existing_fingerprints)
            for raw_eval in legacy_evals
            if isinstance(raw_eval, dict)
        )
        return created_count

    @staticmethod
    def _extract_legacy_evals(legacy_item: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract the list of evaluation dicts from a legacy item, normalizing the fallback case."""
        evals = legacy_item.get("evaluations", [])
        if isinstance(evals, list) and evals:
            return evals
        if "status" in legacy_item:
            return [{"status": legacy_item.get("status"), "evidence": legacy_item.get("evidence")}]
        return []

    def _create_evaluation(
        self,
        session: AsyncSession,
        item: ChecklistItem,
        project_id: str,
        raw_eval: dict[str, Any],
        existing_fingerprints: set[tuple[str, str | None, str, str]],
    ) -> int:
        """Attempt to create one evaluation. Returns 1 if created, 0 if duplicate."""
        normalized_status = self._normalize_evaluation_status(raw_eval.get("status"))
        evidence_value = raw_eval.get("evidence", "")
        evaluator = raw_eval.get("evaluator", "legacy-migration")
        source_id = raw_eval.get("id")
        source_id_str = str(source_id) if source_id else None

        fingerprint = (
            "legacy-migration",
            source_id_str,
            normalized_status.value,
            self._evidence_fingerprint(evidence_value),
        )
        if fingerprint in existing_fingerprints:
            return 0

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
        existing_fingerprints.add(fingerprint)
        return 1

    async def _existing_eval_fingerprints(
        self,
        session: AsyncSession,
        item_id: UUID,
    ) -> set[tuple[str, str | None, str, str]]:
        existing = (
            await session.execute(
                select(ChecklistItemEvaluation).where(
                    ChecklistItemEvaluation.item_id == item_id,
                    ChecklistItemEvaluation.source_type == "legacy-migration",
                )
            )
        ).scalars().all()

        fingerprints: set[tuple[str, str | None, str, str]] = set()
        for entry in existing:
            fingerprints.add(
                (
                    "legacy-migration",
                    entry.source_id,
                    status_value(entry.status),
                    self._evidence_fingerprint(entry.evidence),
                )
            )
        return fingerprints

    @staticmethod
    def _normalize_evaluation_status(raw_status: Any) -> EvaluationStatus:
        normalized = map_legacy_status(str(raw_status or EvaluationStatus.OPEN.value))
        try:
            return EvaluationStatus(normalized)
        except ValueError:
            return EvaluationStatus.OPEN

    @staticmethod
    def _normalize_severity(raw_severity: Any) -> SeverityLevel:
        value = str(raw_severity or SeverityLevel.MEDIUM.value).strip().lower()
        try:
            return SeverityLevel(value)
        except ValueError:
            return SeverityLevel.MEDIUM

    @staticmethod
    def _evidence_fingerprint(evidence: Any) -> str:
        if evidence is None:
            return ""
        if isinstance(evidence, (dict, list)):
            payload = json.dumps(evidence, sort_keys=True, separators=(",", ":"), default=str)
        else:
            payload = str(evidence)
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()  # noqa: S324
