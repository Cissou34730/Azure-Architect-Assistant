"""Dedicated persistence for pending change sets and artifact drafts."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.features.projects.contracts import PendingChangeSetContract
from app.models.project import ArtifactDraftRecord, PendingChangeSetRecord


class PendingChangesRepository:
    """Read and write the dedicated pending-change persistence tables."""

    async def list_change_sets(
        self,
        *,
        project_id: str,
        db: AsyncSession,
    ) -> list[PendingChangeSetContract]:
        result = await db.execute(
            select(PendingChangeSetRecord)
            .options(selectinload(PendingChangeSetRecord.artifact_drafts))
            .where(PendingChangeSetRecord.project_id == project_id)
            .order_by(PendingChangeSetRecord.created_at.asc(), PendingChangeSetRecord.id.asc())
        )
        records = result.scalars().all()
        return [self._hydrate_change_set(record) for record in records]

    async def get_change_set(
        self,
        *,
        project_id: str,
        change_set_id: str,
        db: AsyncSession,
    ) -> PendingChangeSetContract | None:
        result = await db.execute(
            select(PendingChangeSetRecord)
            .options(selectinload(PendingChangeSetRecord.artifact_drafts))
            .where(
                PendingChangeSetRecord.project_id == project_id,
                PendingChangeSetRecord.id == change_set_id,
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None
        return self._hydrate_change_set(record)

    async def sync_from_state(
        self,
        *,
        project_id: str,
        state: Mapping[str, Any],
        db: AsyncSession,
        replace_missing: bool,
    ) -> dict[str, Any]:
        stripped_state = dict(state)
        if "pendingChangeSets" not in stripped_state:
            return stripped_state

        raw_change_sets = stripped_state.pop("pendingChangeSets")
        change_sets = self._validate_change_sets(raw_change_sets)
        if replace_missing:
            await self._delete_missing_change_sets(
                project_id=project_id,
                retained_ids={change_set.id for change_set in change_sets},
                db=db,
            )

        for change_set in change_sets:
            await self._upsert_change_set(
                project_id=project_id,
                change_set=change_set,
                db=db,
            )
        await db.flush()
        return stripped_state

    async def _delete_missing_change_sets(
        self,
        *,
        project_id: str,
        retained_ids: set[str],
        db: AsyncSession,
    ) -> None:
        statement = delete(PendingChangeSetRecord).where(
            PendingChangeSetRecord.project_id == project_id
        )
        if retained_ids:
            statement = statement.where(~PendingChangeSetRecord.id.in_(retained_ids))
        await db.execute(statement)

    async def _upsert_change_set(
        self,
        *,
        project_id: str,
        change_set: PendingChangeSetContract,
        db: AsyncSession,
    ) -> None:
        record = await db.get(PendingChangeSetRecord, change_set.id)
        if record is None:
            record = PendingChangeSetRecord(id=change_set.id, project_id=project_id)
            db.add(record)

        record.project_id = project_id
        record.stage = change_set.stage
        record.status = change_set.status.value
        record.created_at = change_set.created_at
        record.source_message_id = change_set.source_message_id
        record.superseded_by = None
        record.bundle_summary = change_set.bundle_summary
        record.proposed_patch_json = json.dumps(change_set.proposed_patch)
        record.citations_json = json.dumps(change_set.citations)
        record.reviewed_at = change_set.reviewed_at
        record.review_reason = change_set.review_reason
        record.rejection_reason = (
            change_set.review_reason if change_set.status.value == "rejected" else None
        )
        record.waf_delta_json = None
        record.mindmap_delta_json = None

        await db.execute(
            delete(ArtifactDraftRecord).where(ArtifactDraftRecord.change_set_id == change_set.id)
        )
        for draft in change_set.artifact_drafts:
            db.add(
                ArtifactDraftRecord(
                    id=draft.id,
                    change_set_id=change_set.id,
                    artifact_type=draft.artifact_type.value,
                    artifact_id=draft.artifact_id,
                    content_json=json.dumps(draft.content),
                    citations_json=json.dumps(draft.citations),
                    created_at=draft.created_at,
                )
            )

    def _hydrate_change_set(self, record: PendingChangeSetRecord) -> PendingChangeSetContract:
        artifact_drafts = [
            {
                "id": draft.id,
                "artifactType": draft.artifact_type,
                "artifactId": draft.artifact_id,
                "content": self._load_json_object(draft.content_json),
                "citations": self._load_json_list(draft.citations_json),
                "createdAt": draft.created_at,
            }
            for draft in sorted(
                record.artifact_drafts,
                key=lambda item: ((item.created_at or ""), item.id),
            )
        ]
        return PendingChangeSetContract.model_validate(
            {
                "id": record.id,
                "projectId": record.project_id,
                "stage": record.stage,
                "status": record.status,
                "createdAt": record.created_at,
                "sourceMessageId": record.source_message_id,
                "bundleSummary": record.bundle_summary,
                "proposedPatch": self._load_json_object(record.proposed_patch_json),
                "artifactDrafts": artifact_drafts,
                "citations": self._load_json_list(record.citations_json),
                "reviewedAt": record.reviewed_at,
                "reviewReason": record.review_reason,
            }
        )

    def _validate_change_sets(self, raw_change_sets: Any) -> list[PendingChangeSetContract]:
        if raw_change_sets is None:
            return []
        if not isinstance(raw_change_sets, list):
            raise ValueError("Project state contains invalid pendingChangeSets data")

        change_sets: list[PendingChangeSetContract] = []
        for index, raw_change_set in enumerate(raw_change_sets):
            if not isinstance(raw_change_set, dict):
                raise ValueError(
                    f"Project state contains invalid pendingChangeSets item at index {index}"
                )
            change_sets.append(PendingChangeSetContract.model_validate(raw_change_set))
        return change_sets

    def _load_json_object(self, payload: str | None) -> dict[str, Any]:
        if not payload:
            return {}
        value = json.loads(payload)
        if not isinstance(value, dict):
            return {}
        return value

    def _load_json_list(self, payload: str | None) -> list[dict[str, Any]]:
        if not payload:
            return []
        value = json.loads(payload)
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, dict)]


__all__ = ["PendingChangesRepository"]
