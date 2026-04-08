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

        clarification_resolution = proposed_patch.pop("_clarificationResolution", None)
        if clarification_resolution is not None:
            merged_state = self._apply_clarification_resolution(
                current_state=merged_state,
                command=clarification_resolution,
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

    def _apply_clarification_resolution(
        self,
        *,
        current_state: dict[str, Any],
        command: Any,
    ) -> dict[str, Any]:
        if not isinstance(command, dict):
            raise ValueError("Pending clarification resolution payload must be an object.")

        merged_state = deepcopy(current_state)
        requirement_updates = self._as_dict_list(
            command.get("requirements"),
            field_name="requirements",
        )
        question_updates = self._as_dict_list(
            command.get("clarificationQuestions"),
            field_name="clarificationQuestions",
        )
        assumption_updates = self._as_dict_list(
            command.get("assumptions"),
            field_name="assumptions",
        )

        if requirement_updates:
            merged_state["requirements"] = self._apply_list_updates(
                existing_items=merged_state.get("requirements"),
                updates=requirement_updates,
                field_name="requirements",
                require_existing=True,
            )
        if question_updates:
            merged_state["clarificationQuestions"] = self._apply_list_updates(
                existing_items=merged_state.get("clarificationQuestions"),
                updates=question_updates,
                field_name="clarificationQuestions",
                require_existing=True,
            )
        if assumption_updates:
            merged_state["assumptions"] = self._apply_list_updates(
                existing_items=merged_state.get("assumptions"),
                updates=assumption_updates,
                field_name="assumptions",
                require_existing=False,
            )
        return merged_state

    def _apply_list_updates(
        self,
        *,
        existing_items: Any,
        updates: list[dict[str, Any]],
        field_name: str,
        require_existing: bool,
    ) -> list[dict[str, Any]]:
        if existing_items is None:
            items: list[dict[str, Any]] = []
        elif isinstance(existing_items, list):
            items = [dict(item) for item in existing_items if isinstance(item, dict)]
        else:
            raise ValueError(f"Pending clarification resolution requires '{field_name}' to be a list.")

        indexed_items = {
            str(item.get("id")): item
            for item in items
            if str(item.get("id") or "").strip()
        }
        for update in updates:
            item_id = str(update.get("id") or "").strip()
            if not item_id:
                raise ValueError(
                    f"Pending clarification resolution '{field_name}' update must include an id."
                )
            existing_item = indexed_items.get(item_id)
            if existing_item is None:
                if require_existing:
                    raise ValueError(
                        f"Pending clarification resolution '{field_name}' update targets missing id '{item_id}'."
                    )
                new_item = dict(update)
                items.append(new_item)
                indexed_items[item_id] = new_item
                continue
            existing_item.update(update)
        return items

    def _as_dict_list(
        self,
        value: Any,
        *,
        field_name: str,
    ) -> list[dict[str, Any]]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError(f"Pending clarification resolution '{field_name}' must be a list.")
        if not all(isinstance(item, dict) for item in value):
            raise ValueError(
                f"Pending clarification resolution '{field_name}' entries must be objects."
            )
        return [dict(item) for item in value]
