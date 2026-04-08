"""Deterministic merge helpers for pending change-set approval."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.agents_system.services.state_update_parser import merge_state_updates_no_overwrite
from app.features.agent.application.adr_lifecycle_service import ADRLifecycleService
from app.features.projects.contracts import PendingChangeSetContract


class PendingChangeConflictError(ValueError):
    """Raised when approving a change set would overwrite canonical state."""

    def __init__(self, *, conflicts: list[dict[str, Any]]) -> None:
        super().__init__("Pending change set conflicts with canonical project state")
        self.conflicts = conflicts


class PendingChangesMergeService:
    """Apply pending change-set patches to canonical project state."""

    def __init__(
        self,
        *,
        adr_lifecycle_service: ADRLifecycleService | None = None,
    ) -> None:
        self._adr_lifecycle_service = adr_lifecycle_service or ADRLifecycleService()

    def apply_approved_patch(
        self,
        *,
        current_state: dict[str, Any],
        change_set: PendingChangeSetContract,
    ) -> dict[str, Any]:
        proposed_patch = dict(change_set.proposed_patch)
        merged_state = deepcopy(current_state)

        adr_lifecycle_command = proposed_patch.pop("_adrLifecycle", None)
        if adr_lifecycle_command is not None:
            merged_state = self._apply_adr_lifecycle_command(
                current_state=merged_state,
                command=adr_lifecycle_command,
            )

        if not proposed_patch:
            return merged_state

        merged_result = merge_state_updates_no_overwrite(merged_state, proposed_patch)
        if merged_result.conflicts:
            raise PendingChangeConflictError(
                conflicts=[conflict.__dict__ for conflict in merged_result.conflicts]
            )
        return merged_result.merged_state

    def _apply_adr_lifecycle_command(
        self,
        *,
        current_state: dict[str, Any],
        command: Any,
    ) -> dict[str, Any]:
        if not isinstance(command, dict):
            raise ValueError("Pending ADR lifecycle payload must be an object.")

        action = str(command.get("action") or "").strip().lower()
        payload = command.get("adrPayload")
        if not isinstance(payload, dict):
            raise ValueError("Pending ADR lifecycle payload must include adrPayload.")

        if action == "create":
            draft_state, created = self._adr_lifecycle_service.create_adr(
                state=current_state,
                adr_payload=payload,
            )
            accepted_state, _ = self._adr_lifecycle_service.accept_adr(
                state=draft_state,
                adr_id=str(created["id"]).strip(),
            )
            return accepted_state

        if action == "supersede":
            adr_id = str(command.get("adrId") or "").strip()
            if not adr_id:
                raise ValueError("Pending ADR supersede payload must include adrId.")
            superseded_state, _, _ = self._adr_lifecycle_service.supersede_adr(
                state=current_state,
                adr_id=adr_id,
                replacement_payload=payload,
            )
            return superseded_state

        raise ValueError(f"Unsupported pending ADR lifecycle action '{action}'.")
