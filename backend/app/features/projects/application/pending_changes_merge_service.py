"""Deterministic merge helpers for pending change-set approval."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.agents_system.services.state_update_parser import merge_state_updates_no_overwrite
from app.features.projects.contracts import PendingChangeSetContract


class PendingChangeConflictError(ValueError):
    """Raised when approving a change set would overwrite canonical state."""

    def __init__(self, *, conflicts: list[dict[str, Any]]) -> None:
        super().__init__("Pending change set conflicts with canonical project state")
        self.conflicts = conflicts


class PendingChangesMergeService:
    """Apply pending change-set patches to canonical project state."""

    def apply_approved_patch(
        self,
        *,
        current_state: dict[str, Any],
        change_set: PendingChangeSetContract,
    ) -> dict[str, Any]:
        proposed_patch = dict(change_set.proposed_patch)
        if not proposed_patch:
            return deepcopy(current_state)

        merged_result = merge_state_updates_no_overwrite(deepcopy(current_state), proposed_patch)
        if merged_result.conflicts:
            raise PendingChangeConflictError(
                conflicts=[conflict.__dict__ for conflict in merged_result.conflicts]
            )
        return merged_result.merged_state
