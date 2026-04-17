"""Deterministic ADR lifecycle mutations for worker-owned state updates."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from app.agents_system.services.aaa_state_models import (
    AdrArtifact,
    ADRStatus,
    ensure_aaa_defaults,
    generate_traceability_links,
)

_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"accepted", "rejected"},
    "accepted": {"superseded"},
    "rejected": set(),
    "superseded": set(),
}

_LIST_FIELDS = (
    "relatedRequirementIds",
    "relatedMindMapNodeIds",
    "relatedDiagramIds",
    "relatedWafEvidenceIds",
)
_TEXT_FIELDS = (
    "id",
    "title",
    "status",
    "context",
    "decision",
    "consequences",
    "missingEvidenceReason",
    "supersedesAdrId",
    "createdAt",
)


class ADRLifecycleError(ValueError):
    """Raised when an ADR transition or payload is invalid."""


class ADRLifecycleService:
    """Build and transition ADR state while preserving traceability links."""

    def __init__(
        self,
        *,
        id_factory: Callable[[], str] | None = None,
        now_factory: Callable[[], str] | None = None,
    ) -> None:
        self._id_factory = id_factory or (lambda: str(uuid4()))
        self._now_factory = now_factory or self._default_now_factory

    def normalize_state(self, state: Mapping[str, Any] | None) -> dict[str, Any]:
        """Normalize ADR state shape into canonical camelCase payloads."""
        normalized = ensure_aaa_defaults(dict(state or {}))
        normalized_adrs: list[dict[str, Any]] = []
        for adr in normalized.get("adrs") or []:
            try:
                normalized_adrs.append(self._dump_adr(self._validate_adr_payload(adr)))
            except ADRLifecycleError:
                if isinstance(adr, Mapping):
                    normalized_adrs.append(
                        self._normalize_adr_payload(self._to_payload_dict(adr))
                    )
        normalized["adrs"] = normalized_adrs
        normalized["traceabilityLinks"] = self._merge_traceability_links(normalized)
        return normalized

    def create_adr(
        self,
        *,
        state: Mapping[str, Any] | None,
        adr_payload: Mapping[str, Any] | AdrArtifact,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Append a new ADR draft and refresh traceability links."""
        normalized_state = self.normalize_state(state)
        created = self._build_new_adr(adr_payload, default_status="draft")
        created_payload = self._dump_adr(created)
        normalized_state["adrs"] = [*normalized_state["adrs"], created_payload]
        normalized_state["traceabilityLinks"] = self._merge_traceability_links(normalized_state)
        return normalized_state, created_payload

    def transition_adr(
        self,
        *,
        state: Mapping[str, Any] | None,
        adr_id: str,
        target_status: ADRStatus,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Apply a validated lifecycle transition to an existing ADR."""
        normalized_state = self.normalize_state(state)
        index, current = self._find_adr(normalized_state["adrs"], adr_id=adr_id)
        current_status = str(current["status"])
        self._validate_transition(adr_id=adr_id, current_status=current_status, target_status=target_status)

        updated = self._validate_adr_payload({**current, "status": target_status})
        updated_payload = self._dump_adr(updated)
        normalized_state["adrs"][index] = updated_payload
        normalized_state["traceabilityLinks"] = self._merge_traceability_links(normalized_state)
        return normalized_state, updated_payload

    def accept_adr(
        self,
        *,
        state: Mapping[str, Any] | None,
        adr_id: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Promote a draft ADR to accepted."""
        return self.transition_adr(state=state, adr_id=adr_id, target_status="accepted")

    def reject_adr(
        self,
        *,
        state: Mapping[str, Any] | None,
        adr_id: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Mark a draft ADR as rejected."""
        return self.transition_adr(state=state, adr_id=adr_id, target_status="rejected")

    def supersede_adr(
        self,
        *,
        state: Mapping[str, Any] | None,
        adr_id: str,
        replacement_payload: Mapping[str, Any] | AdrArtifact,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        """Mark an ADR superseded and append a replacement ADR."""
        normalized_state, superseded = self.transition_adr(
            state=state,
            adr_id=adr_id,
            target_status="superseded",
        )
        replacement = self._build_superseding_adr(
            previous_adr=superseded,
            replacement_payload=replacement_payload,
        )
        replacement_state = dict(normalized_state)
        replacement_state["adrs"] = [*normalized_state["adrs"], self._dump_adr(replacement)]
        replacement_state["traceabilityLinks"] = self._merge_traceability_links(replacement_state)
        return replacement_state, superseded, self._dump_adr(replacement)

    def _build_new_adr(
        self,
        adr_payload: Mapping[str, Any] | AdrArtifact,
        *,
        default_status: ADRStatus,
    ) -> AdrArtifact:
        payload = self._to_payload_dict(adr_payload)
        payload["id"] = self._id_factory()
        payload["createdAt"] = self._now_factory()
        payload["status"] = default_status
        return self._validate_adr_payload(payload)

    def _build_superseding_adr(
        self,
        *,
        previous_adr: Mapping[str, Any],
        replacement_payload: Mapping[str, Any] | AdrArtifact,
    ) -> AdrArtifact:
        payload = self._to_payload_dict(replacement_payload)
        inherited = self._inherit_traceability_fields(previous_adr=previous_adr, replacement_payload=payload)
        inherited["supersedesAdrId"] = str(previous_adr["id"]).strip()
        inherited["status"] = "accepted"
        inherited["id"] = self._id_factory()
        inherited["createdAt"] = self._now_factory()
        return self._validate_adr_payload(inherited)

    def _inherit_traceability_fields(
        self,
        *,
        previous_adr: Mapping[str, Any],
        replacement_payload: dict[str, Any],
    ) -> dict[str, Any]:
        merged = deepcopy(replacement_payload)
        for field in _LIST_FIELDS:
            incoming = self._normalize_str_list(merged.get(field))
            if incoming:
                merged[field] = incoming
                continue
            merged[field] = self._normalize_str_list(previous_adr.get(field))

        if not merged.get("missingEvidenceReason") and not (
            merged.get("relatedDiagramIds") or merged.get("relatedWafEvidenceIds")
        ):
            merged["missingEvidenceReason"] = previous_adr.get("missingEvidenceReason")
        return merged

    def _find_adr(
        self,
        adrs: list[dict[str, Any]],
        *,
        adr_id: str,
    ) -> tuple[int, dict[str, Any]]:
        normalized_id = adr_id.strip()
        for index, adr in enumerate(adrs):
            if str(adr.get("id") or "").strip() == normalized_id:
                return index, adr
        raise ADRLifecycleError(f"ADR '{normalized_id}' was not found in project state.")

    def _validate_transition(
        self,
        *,
        adr_id: str,
        current_status: str,
        target_status: ADRStatus,
    ) -> None:
        allowed = _ALLOWED_TRANSITIONS.get(current_status, set())
        if target_status not in allowed:
            raise ADRLifecycleError(
                f"Cannot transition ADR '{adr_id}' from {current_status} to {target_status}."
            )

    def _validate_adr_payload(self, payload: Mapping[str, Any] | AdrArtifact) -> AdrArtifact:
        normalized = self._normalize_adr_payload(self._to_payload_dict(payload))
        try:
            return AdrArtifact.model_validate(normalized)
        except ValidationError as exc:
            raise ADRLifecycleError(str(exc)) from exc

    def _normalize_adr_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = deepcopy(payload)
        for field in _TEXT_FIELDS:
            if field in normalized and normalized[field] is not None:
                normalized[field] = str(normalized[field]).strip()
        for field in _LIST_FIELDS:
            if field in normalized:
                normalized[field] = self._normalize_str_list(normalized.get(field))
        return normalized

    def _merge_traceability_links(self, state: Mapping[str, Any]) -> list[dict[str, Any]]:
        merged: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        for link in state.get("traceabilityLinks") or []:
            if not isinstance(link, Mapping):
                continue
            normalized_link = dict(link)
            link_id = str(normalized_link.get("id") or "").strip()
            if not link_id or link_id in seen_ids:
                continue
            merged.append(normalized_link)
            seen_ids.add(link_id)

        for link in generate_traceability_links(dict(state)):
            link_id = str(link.get("id") or "").strip()
            if not link_id or link_id in seen_ids:
                continue
            merged.append(link)
            seen_ids.add(link_id)
        return merged

    def _dump_adr(self, adr: AdrArtifact) -> dict[str, Any]:
        return adr.model_dump(mode="json", by_alias=True, exclude_none=True)

    def _to_payload_dict(self, payload: Mapping[str, Any] | AdrArtifact) -> dict[str, Any]:
        if isinstance(payload, AdrArtifact):
            return payload.model_dump(mode="json", by_alias=True, exclude_none=True)
        return dict(payload)

    def _normalize_str_list(self, values: Any) -> list[str]:
        if not isinstance(values, list):
            return []

        normalized: list[str] = []
        seen: set[str] = set()
        for value in values:
            cleaned = str(value or "").strip()
            if not cleaned or cleaned in seen:
                continue
            normalized.append(cleaned)
            seen.add(cleaned)
        return normalized

    @staticmethod
    def _default_now_factory() -> str:
        return datetime.now(timezone.utc).isoformat()


__all__ = ["ADRLifecycleError", "ADRLifecycleService"]
