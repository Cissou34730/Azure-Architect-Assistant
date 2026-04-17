"""Project-scoped read service for pending change sets."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Protocol

from app.features.projects.application.pending_changes_merge_service import (
    PendingChangesMergeService,
)
from app.features.projects.contracts import (
    ChangeSetReviewResultContract,
    ChangeSetStatus,
    PendingChangeSetContract,
    PendingChangeSetSummaryContract,
)
from app.features.projects.infrastructure.project_state_store import ProjectStateStore


class PendingChangesStateProvider(Protocol):
    async def get_project_state(self, project_id: str, db: Any) -> dict[str, Any]: ...


class PendingChangesStateStore(Protocol):
    async def persist_composed_state(
        self,
        *,
        project_id: str,
        state: dict[str, Any],
        db: Any,
        replace_missing: bool,
        updated_at: str | None = None,
    ) -> dict[str, Any]: ...


class ProjectPendingChangesService:
    """Read pending change sets from the recomposed project state."""

    def __init__(
        self,
        *,
        state_provider: PendingChangesStateProvider,
        state_store: PendingChangesStateStore | None = None,
        merge_service: PendingChangesMergeService | None = None,
    ) -> None:
        self._state_provider = state_provider
        self._state_store = state_store or ProjectStateStore()
        self._merge_service = merge_service or PendingChangesMergeService()

    async def list_pending_changes(
        self,
        *,
        project_id: str,
        db: Any,
        status: ChangeSetStatus | None = None,
    ) -> list[PendingChangeSetSummaryContract]:
        change_sets = await self._load_change_sets(project_id=project_id, db=db)
        if status is not None:
            change_sets = [change for change in change_sets if change.status is status]

        return [
            PendingChangeSetSummaryContract(
                id=change.id,
                projectId=change.project_id,
                stage=change.stage,
                status=change.status,
                createdAt=change.created_at,
                sourceMessageId=change.source_message_id,
                bundleSummary=change.bundle_summary,
                artifactCount=len(change.artifact_drafts),
            )
            for change in change_sets
        ]

    async def get_pending_change(
        self,
        *,
        project_id: str,
        change_set_id: str,
        db: Any,
    ) -> PendingChangeSetContract:
        for change in await self._load_change_sets(project_id=project_id, db=db):
            if change.id == change_set_id:
                return change
        raise ValueError("Change set not found")

    async def approve_pending_change(
        self,
        *,
        project_id: str,
        change_set_id: str,
        reason: str | None = None,
        db: Any,
    ) -> ChangeSetReviewResultContract:
        state, raw_change_sets = await self._load_state_with_raw_change_sets(project_id=project_id, db=db)
        change_set, raw_change_set = self._find_change_set(
            change_set_id=change_set_id,
            raw_change_sets=raw_change_sets,
        )
        self._assert_pending(change_set)

        merged_state = self._merge_service.apply_approved_patch(
            current_state=state,
            change_set=change_set,
        )
        timestamp = datetime.now(timezone.utc).isoformat()
        raw_change_set["status"] = ChangeSetStatus.APPROVED.value
        raw_change_set["reviewedAt"] = timestamp
        raw_change_set["reviewReason"] = reason
        merged_state["pendingChangeSets"] = raw_change_sets

        await self._persist_state(
            project_id=project_id,
            db=db,
            state=merged_state,
            updated_at=timestamp,
        )
        return ChangeSetReviewResultContract(
            changeSet=PendingChangeSetContract.model_validate(raw_change_set),
            projectState=merged_state,
            conflicts=[],
        )

    async def reject_pending_change(
        self,
        *,
        project_id: str,
        change_set_id: str,
        reason: str | None = None,
        db: Any,
    ) -> ChangeSetReviewResultContract:
        return await self._review_without_merge(
            project_id=project_id,
            change_set_id=change_set_id,
            reason=reason,
            target_status=ChangeSetStatus.REJECTED,
            db=db,
        )

    async def revise_pending_change(
        self,
        *,
        project_id: str,
        change_set_id: str,
        reason: str | None = None,
        db: Any,
    ) -> ChangeSetReviewResultContract:
        return await self._review_without_merge(
            project_id=project_id,
            change_set_id=change_set_id,
            reason=reason,
            target_status=ChangeSetStatus.SUPERSEDED,
            db=db,
        )

    async def record_pending_change(
        self,
        *,
        project_id: str,
        change_set: PendingChangeSetContract,
        db: Any,
    ) -> PendingChangeSetContract:
        state, raw_change_sets = await self._load_state_with_raw_change_sets(project_id=project_id, db=db)
        payload = change_set.model_dump(mode="json", by_alias=True, exclude_none=True)
        raw_change_sets.append(payload)
        state["pendingChangeSets"] = raw_change_sets
        timestamp = datetime.now(timezone.utc).isoformat()
        await self._persist_state(
            project_id=project_id,
            db=db,
            state=state,
            updated_at=timestamp,
        )
        return PendingChangeSetContract.model_validate(payload)

    async def _load_change_sets(
        self,
        *,
        project_id: str,
        db: Any,
    ) -> list[PendingChangeSetContract]:
        state = await self._state_provider.get_project_state(project_id, db)
        raw_change_sets = state.get("pendingChangeSets", [])
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

    async def _load_state_with_raw_change_sets(
        self,
        *,
        project_id: str,
        db: Any,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        state = deepcopy(await self._state_provider.get_project_state(project_id, db))
        raw_change_sets = state.get("pendingChangeSets", [])
        if raw_change_sets is None:
            raw_change_sets = []
        if not isinstance(raw_change_sets, list):
            raise ValueError("Project state contains invalid pendingChangeSets data")
        validated: list[dict[str, Any]] = []
        for index, raw_change_set in enumerate(raw_change_sets):
            if not isinstance(raw_change_set, dict):
                raise ValueError(
                    f"Project state contains invalid pendingChangeSets item at index {index}"
                )
            validated.append(raw_change_set)
        return state, validated

    def _find_change_set(
        self,
        *,
        change_set_id: str,
        raw_change_sets: list[dict[str, Any]],
    ) -> tuple[PendingChangeSetContract, dict[str, Any]]:
        for raw_change_set in raw_change_sets:
            change_set = PendingChangeSetContract.model_validate(raw_change_set)
            if change_set.id == change_set_id:
                return change_set, raw_change_set
        raise ValueError("Change set not found")

    def _assert_pending(self, change_set: PendingChangeSetContract) -> None:
        if change_set.status is not ChangeSetStatus.PENDING:
            raise ValueError(f"Change set is already {change_set.status.value}")

    async def _review_without_merge(
        self,
        *,
        project_id: str,
        change_set_id: str,
        reason: str | None,
        target_status: ChangeSetStatus,
        db: Any,
    ) -> ChangeSetReviewResultContract:
        state, raw_change_sets = await self._load_state_with_raw_change_sets(project_id=project_id, db=db)
        change_set, raw_change_set = self._find_change_set(
            change_set_id=change_set_id,
            raw_change_sets=raw_change_sets,
        )
        self._assert_pending(change_set)

        timestamp = datetime.now(timezone.utc).isoformat()
        raw_change_set["status"] = target_status.value
        raw_change_set["reviewedAt"] = timestamp
        raw_change_set["reviewReason"] = reason
        state["pendingChangeSets"] = raw_change_sets

        await self._persist_state(
            project_id=project_id,
            db=db,
            state=state,
            updated_at=timestamp,
        )
        return ChangeSetReviewResultContract(
            changeSet=PendingChangeSetContract.model_validate(raw_change_set),
            projectState=None,
            conflicts=[],
        )

    async def _persist_state(
        self,
        *,
        project_id: str,
        db: Any,
        state: dict[str, Any],
        updated_at: str,
    ) -> None:
        await self._state_store.persist_composed_state(
            project_id=project_id,
            state=state,
            db=db,
            replace_missing=False,
            updated_at=updated_at,
        )
        await db.commit()
