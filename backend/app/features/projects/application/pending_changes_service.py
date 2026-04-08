"""Project-scoped read service for pending change sets."""

from __future__ import annotations

from typing import Any, Protocol

from app.features.projects.contracts import (
    ChangeSetStatus,
    PendingChangeSetContract,
    PendingChangeSetSummaryContract,
)


class PendingChangesStateProvider(Protocol):
    async def get_project_state(self, project_id: str, db: object) -> dict[str, Any]: ...


class ProjectPendingChangesService:
    """Read pending change sets from the recomposed project state."""

    def __init__(self, *, state_provider: PendingChangesStateProvider) -> None:
        self._state_provider = state_provider

    async def list_pending_changes(
        self,
        *,
        project_id: str,
        db: object,
        status: ChangeSetStatus | None = None,
    ) -> list[PendingChangeSetSummaryContract]:
        change_sets = await self._load_change_sets(project_id=project_id, db=db)
        if status is not None:
            change_sets = [change for change in change_sets if change.status is status]

        return [
            PendingChangeSetSummaryContract(
                id=change.id,
                project_id=change.project_id,
                stage=change.stage,
                status=change.status,
                created_at=change.created_at,
                source_message_id=change.source_message_id,
                bundle_summary=change.bundle_summary,
                artifact_count=len(change.artifact_drafts),
            )
            for change in change_sets
        ]

    async def get_pending_change(
        self,
        *,
        project_id: str,
        change_set_id: str,
        db: object,
    ) -> PendingChangeSetContract:
        for change in await self._load_change_sets(project_id=project_id, db=db):
            if change.id == change_set_id:
                return change
        raise ValueError("Change set not found")

    async def _load_change_sets(
        self,
        *,
        project_id: str,
        db: object,
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
