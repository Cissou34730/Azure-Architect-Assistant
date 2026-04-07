"""Persistence helpers for checklist synchronization."""

from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.checklists.infrastructure.models import (
    Checklist,
    ChecklistItem,
    ChecklistItemEvaluation,
    ChecklistTemplate,
    EvaluationStatus,
    SeverityLevel,
)
from app.features.checklists.infrastructure.template_resolver import ChecklistTemplateResolver


class ChecklistSyncWriter:
    """Persistence helper for templates/checklists/items/evaluations."""

    def __init__(self, resolver: ChecklistTemplateResolver, namespace_uuid: UUID) -> None:
        self.resolver = resolver
        self.namespace_uuid = namespace_uuid

    async def get_or_create_template_record(
        self,
        session: AsyncSession,
        template: ChecklistTemplate,
    ) -> ChecklistTemplate:
        existing = (
            await session.execute(select(ChecklistTemplate).where(ChecklistTemplate.slug == template.slug))
        ).scalar_one_or_none()
        if existing is not None:
            return existing

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
        savepoint = await session.begin_nested()
        try:
            session.add(record)
            await session.flush()
            await savepoint.commit()
            return record
        except IntegrityError:
            await savepoint.rollback()
            winner = (
                await session.execute(select(ChecklistTemplate).where(ChecklistTemplate.slug == template.slug))
            ).scalar_one_or_none()
            if winner is None:
                raise
            return winner

    async def get_or_create_checklist(
        self,
        session: AsyncSession,
        project_id: str,
        template: ChecklistTemplate,
    ) -> Checklist:
        existing = (
            await session.execute(
                select(Checklist).where(
                    and_(Checklist.project_id == project_id, Checklist.template_slug == template.slug)
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing

        checklist = Checklist(
            project_id=project_id,
            template_id=template.id,
            template_slug=template.slug,
            title=template.title,
            version=template.version,
        )
        savepoint = await session.begin_nested()
        try:
            session.add(checklist)
            await session.flush()
            await savepoint.commit()
            return checklist
        except IntegrityError:
            await savepoint.rollback()
            winner = (
                await session.execute(
                    select(Checklist).where(
                        and_(Checklist.project_id == project_id, Checklist.template_slug == template.slug)
                    )
                )
            ).scalar_one_or_none()
            if winner is None:
                raise
            return winner

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
        existing = await session.get(ChecklistItem, deterministic_id)
        if existing is not None:
            return existing

        metadata = self.resolver.metadata_for_item(template, template_item_id)
        item_payload = legacy_item or {}
        title = str(
            metadata.get("title")
            or item_payload.get("topic")
            or item_payload.get("title")
            or template_item_id
        )
        pillar = str(metadata.get("pillar") or item_payload.get("pillar") or "General")
        description = str(metadata.get("description") or "")
        severity = self._normalize_severity(
            metadata.get("severity") or metadata.get("priority") or item_payload.get("severity")
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
        savepoint = await session.begin_nested()
        try:
            session.add(item)
            await session.flush()
            await savepoint.commit()
            return item
        except IntegrityError:
            await savepoint.rollback()
            winner = await session.get(ChecklistItem, deterministic_id)
            if winner is None:
                raise
            return winner

    async def sync_item_from_payload(
        self,
        session: AsyncSession,
        checklist: Checklist,
        item_payload: dict[str, Any],
        template: ChecklistTemplate,
        project_id: str,
    ) -> int:
        item_slug = str(item_payload.get("id") or item_payload.get("slug") or "").strip()
        if not item_slug:
            return 0

        item = await self.get_or_create_item(
            session=session,
            checklist=checklist,
            template_item_id=item_slug,
            template=template,
            legacy_item=item_payload,
        )

        eval_payloads = self._extract_item_evaluations(item_payload)
        if not eval_payloads:
            return 0

        existing_fingerprints = await self._existing_eval_fingerprints(session, item.id)
        created_count = 0
        for raw_eval in eval_payloads:
            if not isinstance(raw_eval, dict):
                continue
            created_count += self._create_evaluation_entry(
                session,
                item,
                project_id,
                raw_eval,
                existing_fingerprints,
            )
        return created_count

    @staticmethod
    def _extract_item_evaluations(item_payload: dict[str, Any]) -> list[dict[str, Any]]:
        evals = item_payload.get("evaluations", [])
        if isinstance(evals, list) and evals:
            return [entry for entry in evals if isinstance(entry, dict)]
        if "status" in item_payload:
            return [
                {
                    "status": item_payload.get("status"),
                    "evidence": item_payload.get("evidence"),
                    "sourceType": "legacy-bridge",
                }
            ]
        return []

    def _create_evaluation_entry(
        self,
        session: AsyncSession,
        item: ChecklistItem,
        project_id: str,
        raw_eval: dict[str, Any],
        existing_fingerprints: set[tuple[str, str | None, str, str]],
    ) -> int:
        status = self._normalize_evaluation_status(raw_eval.get("status"))
        source_type = str(raw_eval.get("sourceType") or raw_eval.get("source_type") or "agent-validation")
        source_id_raw = raw_eval.get("id") or raw_eval.get("sourceId") or raw_eval.get("source_id")
        source_id = str(source_id_raw) if source_id_raw else None
        evidence_value = raw_eval.get("evidence")

        fingerprint = (
            source_type,
            source_id,
            status.value,
            self._hash_evidence(evidence_value),
        )
        if fingerprint in existing_fingerprints:
            return 0

        evaluation = ChecklistItemEvaluation(
            item_id=item.id,
            project_id=project_id,
            status=status,
            comment=raw_eval.get("comment"),
            evidence=evidence_value,
            evaluator=str(raw_eval.get("evaluator", "agent")),
            source_type=source_type,
            source_id=source_id,
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
                select(ChecklistItemEvaluation).where(ChecklistItemEvaluation.item_id == item_id)
            )
        ).scalars().all()

        fingerprints: set[tuple[str, str | None, str, str]] = set()
        for entry in existing:
            raw_status = entry.status.value if isinstance(entry.status, EvaluationStatus) else str(entry.status)
            fingerprints.add(
                (
                    str(entry.source_type or "agent-validation"),
                    str(entry.source_id) if entry.source_id is not None else None,
                    raw_status,
                    self._hash_evidence(entry.evidence),
                )
            )
        return fingerprints

    @staticmethod
    def _normalize_evaluation_status(raw_status: Any) -> EvaluationStatus:
        value = str(raw_status or EvaluationStatus.OPEN.value).strip().lower().replace("-", "_")
        if value == EvaluationStatus.FIXED.value:
            return EvaluationStatus.FIXED
        if value == EvaluationStatus.IN_PROGRESS.value:
            return EvaluationStatus.IN_PROGRESS
        if value == EvaluationStatus.FALSE_POSITIVE.value:
            return EvaluationStatus.FALSE_POSITIVE
        return EvaluationStatus.OPEN

    @staticmethod
    def _normalize_severity(raw_severity: Any) -> SeverityLevel:
        value = str(raw_severity or SeverityLevel.MEDIUM.value).strip().lower()
        try:
            return SeverityLevel(value)
        except ValueError:
            return SeverityLevel.MEDIUM

    @staticmethod
    def _hash_evidence(evidence: Any) -> str:
        if evidence is None:
            return ""
        if isinstance(evidence, (dict, list)):
            payload = json.dumps(evidence, sort_keys=True, separators=(",", ":"), default=str)
        else:
            payload = str(evidence)
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()  # noqa: S324

