"""Persistence helpers for decomposed project architecture inputs."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import ProjectArchitectureInputs

logger = logging.getLogger(__name__)

ARCHITECTURE_INPUT_FIELD_MAP: dict[str, str] = {
    "context": "context_json",
    "nfrs": "nfrs_json",
    "applicationStructure": "application_structure_json",
    "dataCompliance": "data_compliance_json",
    "technicalConstraints": "technical_constraints_json",
    "openQuestions": "open_questions_json",
}


def extract_architecture_inputs(state: Mapping[str, Any]) -> dict[str, Any]:
    """Return the architecture-input subset of a project state payload."""
    return {
        key: state[key]
        for key in ARCHITECTURE_INPUT_FIELD_MAP
        if key in state
    }


def strip_architecture_inputs(state: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copy of *state* without decomposed architecture-input keys."""
    return {
        key: value
        for key, value in state.items()
        if key not in ARCHITECTURE_INPUT_FIELD_MAP
    }


def merge_architecture_inputs(
    state: Mapping[str, Any],
    architecture_inputs: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Overlay decomposed architecture inputs onto a legacy blob payload."""
    merged = dict(state)
    if architecture_inputs is None:
        return merged

    for key in ARCHITECTURE_INPUT_FIELD_MAP:
        if key in architecture_inputs:
            merged[key] = architecture_inputs[key]
    return merged


class ProjectArchitectureInputsRepository:
    """Load and persist decomposed architecture-input state."""

    async def get_architecture_inputs(
        self,
        *,
        project_id: str,
        db: AsyncSession,
    ) -> dict[str, Any] | None:
        result = await db.execute(
            select(ProjectArchitectureInputs).where(ProjectArchitectureInputs.project_id == project_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None

        payload: dict[str, Any] = {}
        for state_key, column_name in ARCHITECTURE_INPUT_FIELD_MAP.items():
            raw_value = getattr(row, column_name)
            value = self._deserialize(raw_value, project_id=project_id, state_key=state_key)
            if value is not None:
                payload[state_key] = value

        return payload or None

    async def sync_from_state(
        self,
        *,
        project_id: str,
        state: Mapping[str, Any],
        db: AsyncSession,
        replace_missing: bool,
        updated_at: str | None = None,
    ) -> dict[str, Any]:
        architecture_inputs = extract_architecture_inputs(state)
        await self.upsert_architecture_inputs(
            project_id=project_id,
            architecture_inputs=architecture_inputs,
            db=db,
            replace_missing=replace_missing,
            updated_at=updated_at,
        )
        return strip_architecture_inputs(state)

    async def upsert_architecture_inputs(
        self,
        *,
        project_id: str,
        architecture_inputs: Mapping[str, Any],
        db: AsyncSession,
        replace_missing: bool,
        updated_at: str | None = None,
    ) -> None:
        result = await db.execute(
            select(ProjectArchitectureInputs).where(ProjectArchitectureInputs.project_id == project_id)
        )
        row = result.scalar_one_or_none()

        if row is None and not architecture_inputs:
            return

        if row is None:
            row = ProjectArchitectureInputs(
                project_id=project_id,
                updated_at=updated_at or self._now_iso(),
            )
            db.add(row)

        for state_key, column_name in ARCHITECTURE_INPUT_FIELD_MAP.items():
            if state_key in architecture_inputs:
                setattr(row, column_name, json.dumps(architecture_inputs[state_key]))
            elif replace_missing:
                setattr(row, column_name, None)

        if self._row_is_empty(row):
            await db.delete(row)
            await db.flush()
            return

        row.updated_at = updated_at or self._now_iso()
        await db.flush()

    def _deserialize(
        self,
        raw_value: str | None,
        *,
        project_id: str,
        state_key: str,
    ) -> Any | None:
        if raw_value in (None, ""):
            return None

        try:
            return json.loads(raw_value)
        except json.JSONDecodeError:
            logger.warning(
                "Failed to deserialize %s architecture inputs for project %s",
                state_key,
                project_id,
            )
            return None

    def _row_is_empty(self, row: ProjectArchitectureInputs) -> bool:
        return all(
            getattr(row, column_name) in (None, "")
            for column_name in ARCHITECTURE_INPUT_FIELD_MAP.values()
        )

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()


__all__ = [
    "ARCHITECTURE_INPUT_FIELD_MAP",
    "ProjectArchitectureInputsRepository",
    "extract_architecture_inputs",
    "merge_architecture_inputs",
    "strip_architecture_inputs",
]
