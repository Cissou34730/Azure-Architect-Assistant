"""Worker helpers for explicit ADR drafting and supersession bundles."""

from __future__ import annotations

import inspect
import uuid
from collections.abc import Awaitable, Callable, Mapping
from datetime import datetime, timezone
from typing import Any, Protocol

from app.agents_system.services.adr_drafter_worker import (
    ADRDraftAction,
    ADRDraftEnvelope,
    ADRDrafterWorker,
)
from app.features.agent.application.adr_lifecycle_service import ADRLifecycleService
from app.features.projects.contracts import (
    ArtifactDraftType,
    ChangeSetStatus,
    PendingChangeSetContract,
)


class PendingChangeRecorder(Protocol):
    async def record_pending_change(
        self,
        *,
        project_id: str,
        change_set: PendingChangeSetContract,
        db: object,
    ) -> PendingChangeSetContract: ...


class ADRManagementWorker:
    """Draft ADR bundles and persist them as reviewable pending change sets."""

    def __init__(
        self,
        *,
        drafter: ADRDrafterWorker | Any,
        pending_change_recorder: PendingChangeRecorder,
        lifecycle_service: ADRLifecycleService | None = None,
        change_set_id_factory: Callable[[], str] | None = None,
        artifact_id_factory: Callable[[], str] | None = None,
        now_factory: Callable[[], str] | None = None,
    ) -> None:
        self._drafter = drafter
        self._pending_change_recorder = pending_change_recorder
        self._lifecycle_service = lifecycle_service or ADRLifecycleService()
        self._change_set_id_factory = change_set_id_factory or (lambda: str(uuid.uuid4()))
        self._artifact_id_factory = artifact_id_factory or (lambda: str(uuid.uuid4()))
        self._now_factory = now_factory or self._default_now_factory

    async def draft_and_record_pending_change(
        self,
        *,
        project_id: str,
        user_message: str,
        project_state: Mapping[str, Any] | None,
        db: object,
        source_message_id: str | None = None,
    ) -> PendingChangeSetContract:
        normalized_state = self._lifecycle_service.normalize_state(project_state)
        requested_action = self._detect_action(user_message=user_message, project_state=normalized_state)
        target_adr = None
        if requested_action == "supersede":
            target_adr = self._select_superseded_adr(
                user_message=user_message,
                project_state=normalized_state,
                preferred_adr_id=None,
            )

        draft_response = self._drafter.draft_adr(
            user_message=user_message,
            project_state=normalized_state,
            requested_action=requested_action,
            target_adr=target_adr,
        )
        if inspect.isawaitable(draft_response):
            draft_response = await draft_response
        draft = self._coerce_draft_envelope(draft_response)

        if draft.action == "supersede":
            target_adr = self._select_superseded_adr(
                user_message=user_message,
                project_state=normalized_state,
                preferred_adr_id=draft.adr.supersedes_adr_id,
            )
            replacement_payload = self._lifecycle_payload(draft)
            replacement_payload["supersedesAdrId"] = str(target_adr["id"]).strip()
            _, superseded_preview, replacement_preview = self._lifecycle_service.supersede_adr(
                state=normalized_state,
                adr_id=str(target_adr["id"]).strip(),
                replacement_payload=replacement_payload,
            )
            change_set = self._build_supersede_change_set(
                project_id=project_id,
                source_message_id=source_message_id,
                superseded_preview=superseded_preview,
                replacement_preview=replacement_preview,
                draft=draft,
            )
        else:
            adr_payload = self._lifecycle_payload(draft)
            _, created_preview = self._lifecycle_service.create_adr(
                state=normalized_state,
                adr_payload=adr_payload,
            )
            change_set = self._build_create_change_set(
                project_id=project_id,
                source_message_id=source_message_id,
                created_preview=created_preview,
                draft=draft,
            )

        return await self._pending_change_recorder.record_pending_change(
            project_id=project_id,
            change_set=change_set,
            db=db,
        )

    def _build_create_change_set(
        self,
        *,
        project_id: str,
        source_message_id: str | None,
        created_preview: Mapping[str, Any],
        draft: ADRDraftEnvelope,
    ) -> PendingChangeSetContract:
        draft_payload = dict(created_preview)
        draft_payload["alternativesConsidered"] = list(draft.adr.alternatives_considered)
        created_at = self._now_factory()
        return PendingChangeSetContract(
            id=self._change_set_id_factory(),
            project_id=project_id,
            stage="manage_adr",
            status=ChangeSetStatus.PENDING,
            created_at=created_at,
            source_message_id=source_message_id,
            bundle_summary=f"Draft ADR '{draft.adr.title}' for approval",
            proposed_patch={
                "_adrLifecycle": {
                    "action": "create",
                    "adrPayload": self._lifecycle_payload(draft),
                    "draftMetadata": {
                        "alternativesConsidered": list(draft.adr.alternatives_considered),
                    },
                }
            },
            artifact_drafts=[
                {
                    "id": self._artifact_id_factory(),
                    "artifactType": ArtifactDraftType.ADR.value,
                    "artifactId": created_preview.get("id"),
                    "content": draft_payload,
                    "citations": list(created_preview.get("sourceCitations") or []),
                    "createdAt": created_preview.get("createdAt"),
                }
            ],
        )

    def _build_supersede_change_set(
        self,
        *,
        project_id: str,
        source_message_id: str | None,
        superseded_preview: Mapping[str, Any],
        replacement_preview: Mapping[str, Any],
        draft: ADRDraftEnvelope,
    ) -> PendingChangeSetContract:
        replacement_payload = dict(replacement_preview)
        replacement_payload["alternativesConsidered"] = list(draft.adr.alternatives_considered)
        created_at = self._now_factory()
        target_adr_id = str(superseded_preview.get("id") or "").strip()
        return PendingChangeSetContract(
            id=self._change_set_id_factory(),
            project_id=project_id,
            stage="manage_adr",
            status=ChangeSetStatus.PENDING,
            created_at=created_at,
            source_message_id=source_message_id,
            bundle_summary=(
                f"Supersede ADR '{superseded_preview.get('title')}' with '{draft.adr.title}'"
            ),
            proposed_patch={
                "_adrLifecycle": {
                    "action": "supersede",
                    "adrId": target_adr_id,
                    "adrPayload": self._lifecycle_payload(draft, supersedes_adr_id=target_adr_id),
                    "draftMetadata": {
                        "alternativesConsidered": list(draft.adr.alternatives_considered),
                    },
                }
            },
            artifact_drafts=[
                {
                    "id": self._artifact_id_factory(),
                    "artifactType": ArtifactDraftType.ADR.value,
                    "artifactId": superseded_preview.get("id"),
                    "content": dict(superseded_preview),
                    "citations": list(superseded_preview.get("sourceCitations") or []),
                    "createdAt": superseded_preview.get("createdAt"),
                },
                {
                    "id": self._artifact_id_factory(),
                    "artifactType": ArtifactDraftType.ADR.value,
                    "artifactId": replacement_preview.get("id"),
                    "content": replacement_payload,
                    "citations": list(replacement_preview.get("sourceCitations") or []),
                    "createdAt": replacement_preview.get("createdAt"),
                },
            ],
        )

    def _detect_action(
        self,
        *,
        user_message: str,
        project_state: Mapping[str, Any],
    ) -> ADRDraftAction:
        message = user_message.lower()
        has_adrs = bool(project_state.get("adrs"))
        if not has_adrs:
            return "create"
        if "supersede" in message:
            return "supersede"
        if "replace" in message and ("adr" in message or "decision" in message):
            return "supersede"
        return "create"

    def _select_superseded_adr(
        self,
        *,
        user_message: str,
        project_state: Mapping[str, Any],
        preferred_adr_id: str | None,
    ) -> dict[str, Any]:
        adrs = [
            dict(adr)
            for adr in project_state.get("adrs") or []
            if isinstance(adr, Mapping)
        ]
        accepted = [
            adr
            for adr in adrs
            if str(adr.get("status") or "").strip().lower() == "accepted"
        ]
        if not accepted:
            raise ValueError("Supersede flow requires an accepted ADR in canonical state.")

        preferred_id = str(preferred_adr_id or "").strip()
        if preferred_id:
            for adr in accepted:
                if str(adr.get("id") or "").strip() == preferred_id:
                    return adr

        message = user_message.lower()
        matched = [
            adr
            for adr in accepted
            if str(adr.get("id") or "").strip().lower() in message
            or str(adr.get("title") or "").strip().lower() in message
        ]
        if len(matched) == 1:
            return matched[0]
        if not matched and len(accepted) == 1:
            return accepted[0]
        raise ValueError("Unable to determine which ADR to supersede. Specify the ADR id or exact title.")

    def _coerce_draft_envelope(self, draft_response: ADRDraftEnvelope | Mapping[str, Any]) -> ADRDraftEnvelope:
        if isinstance(draft_response, ADRDraftEnvelope):
            return draft_response
        return ADRDraftEnvelope.model_validate(draft_response)

    def _lifecycle_payload(
        self,
        draft: ADRDraftEnvelope,
        *,
        supersedes_adr_id: str | None = None,
    ) -> dict[str, Any]:
        payload = draft.adr.model_dump(mode="json", by_alias=True, exclude_none=True)
        if supersedes_adr_id:
            payload["supersedesAdrId"] = supersedes_adr_id
        return payload

    @staticmethod
    def _default_now_factory() -> str:
        return datetime.now(timezone.utc).isoformat()


def create_adr_management_worker() -> ADRManagementWorker:
    """Build the shared ADR management worker."""
    from app.features.projects.application.chat_service import ChatService
    from app.features.projects.application.pending_changes_service import (
        ProjectPendingChangesService,
    )

    pending_changes_service = ProjectPendingChangesService(state_provider=ChatService())
    return ADRManagementWorker(
        drafter=ADRDrafterWorker(),
        pending_change_recorder=pending_changes_service,
    )


__all__ = ["ADRManagementWorker", "PendingChangeRecorder", "create_adr_management_worker"]
