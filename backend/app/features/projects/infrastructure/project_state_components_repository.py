"""Persistence helpers for decomposed top-level ProjectState component families."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import ProjectStateComponent

logger = logging.getLogger(__name__)

PROJECT_STATE_COMPONENT_SOURCES: dict[str, tuple[str, ...]] = {
    "requirements": ("requirements",),
    "assumptions": ("assumptions",),
    "clarificationQuestions": ("clarificationQuestions",),
    "candidateArchitectures": ("candidateArchitectures",),
    "adrs": ("adrs",),
    "findings": ("findings",),
    "diagrams": ("diagrams",),
    "iacArtifacts": ("iacArtifacts",),
    "costEstimates": ("costEstimates",),
    "traceabilityLinks": ("traceabilityLinks",),
    "traceabilityIssues": ("traceabilityIssues",),
    "mindMapCoverage": ("mindMapCoverage",),
    "mindMap": ("mindMap",),
    "referenceDocuments": ("referenceDocuments",),
    "mcpQueries": ("mcpQueries",),
    "iterationEvents": ("iterationEvents",),
    "analysisSummary": ("analysisSummary",),
    "projectDocumentStats": ("projectDocumentStats", "ingestionStats"),
}

PROJECT_STATE_COMPONENT_KEYS: tuple[str, ...] = tuple(PROJECT_STATE_COMPONENT_SOURCES.keys())
PROJECT_STATE_COMPONENT_ALIAS_KEYS: frozenset[str] = frozenset(
    source_key
    for source_keys in PROJECT_STATE_COMPONENT_SOURCES.values()
    for source_key in source_keys
)


def extract_project_state_components(state: Mapping[str, Any]) -> dict[str, Any]:
    """Return the decomposed ProjectState component subset for persistence."""
    components: dict[str, Any] = {}
    for component_key, source_keys in PROJECT_STATE_COMPONENT_SOURCES.items():
        for source_key in source_keys:
            if source_key not in state:
                continue
            value = state[source_key]
            if value is None:
                continue
            components[component_key] = value
            break
    return components


def strip_project_state_components(state: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copy of *state* without decomposed component keys or aliases."""
    return {
        key: value
        for key, value in state.items()
        if key not in PROJECT_STATE_COMPONENT_ALIAS_KEYS
    }


def merge_project_state_components(
    state: Mapping[str, Any],
    components: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Overlay decomposed component families onto a legacy blob payload."""
    merged = dict(state)
    if components is None:
        return merged

    for component_key in PROJECT_STATE_COMPONENT_KEYS:
        if component_key in components:
            merged[component_key] = components[component_key]
    return merged


class ProjectStateComponentsRepository:
    """Load and persist decomposed top-level ProjectState component families."""

    async def get_project_state_components(
        self,
        *,
        project_id: str,
        db: AsyncSession,
    ) -> dict[str, Any] | None:
        result = await db.execute(
            select(ProjectStateComponent).where(ProjectStateComponent.project_id == project_id)
        )
        rows = result.scalars().all()
        if not rows:
            return None

        payload: dict[str, Any] = {}
        for row in rows:
            if row.component_key not in PROJECT_STATE_COMPONENT_SOURCES:
                continue
            value = self._deserialize(
                row.payload_json,
                project_id=project_id,
                component_key=row.component_key,
            )
            if value is not None:
                payload[row.component_key] = value

        return payload or None

    async def backfill_missing_from_state(
        self,
        *,
        project_id: str,
        state: Mapping[str, Any],
        db: AsyncSession,
        updated_at: str | None = None,
    ) -> None:
        components = extract_project_state_components(state)
        if not components:
            return

        result = await db.execute(
            select(ProjectStateComponent).where(ProjectStateComponent.project_id == project_id)
        )
        existing_rows = {row.component_key: row for row in result.scalars().all()}

        for component_key, payload in components.items():
            if component_key in existing_rows:
                continue
            db.add(
                ProjectStateComponent(
                    project_id=project_id,
                    component_key=component_key,
                    payload_json=json.dumps(payload),
                    updated_at=updated_at or self._now_iso(),
                )
            )

        await db.flush()

    async def sync_from_state(
        self,
        *,
        project_id: str,
        state: Mapping[str, Any],
        db: AsyncSession,
        replace_missing: bool,
        updated_at: str | None = None,
    ) -> dict[str, Any]:
        components = extract_project_state_components(state)
        await self.upsert_project_state_components(
            project_id=project_id,
            components=components,
            db=db,
            replace_missing=replace_missing,
            updated_at=updated_at,
        )
        return strip_project_state_components(state)

    async def upsert_project_state_components(
        self,
        *,
        project_id: str,
        components: Mapping[str, Any],
        db: AsyncSession,
        replace_missing: bool,
        updated_at: str | None = None,
    ) -> None:
        result = await db.execute(
            select(ProjectStateComponent).where(ProjectStateComponent.project_id == project_id)
        )
        existing_rows = {row.component_key: row for row in result.scalars().all()}

        for component_key in PROJECT_STATE_COMPONENT_KEYS:
            row = existing_rows.get(component_key)
            if component_key in components:
                if row is None:
                    row = ProjectStateComponent(
                        project_id=project_id,
                        component_key=component_key,
                        payload_json=json.dumps(components[component_key]),
                        updated_at=updated_at or self._now_iso(),
                    )
                    db.add(row)
                else:
                    row.payload_json = json.dumps(components[component_key])
                    row.updated_at = updated_at or self._now_iso()
            elif replace_missing and row is not None:
                await db.delete(row)

        await db.flush()

    def _deserialize(
        self,
        raw_value: str | None,
        *,
        project_id: str,
        component_key: str,
    ) -> Any | None:
        if raw_value in (None, ""):
            return None

        try:
            return json.loads(raw_value)
        except json.JSONDecodeError:
            logger.warning(
                "Failed to deserialize %s component payload for project %s",
                component_key,
                project_id,
            )
            return None

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()


__all__ = [
    "PROJECT_STATE_COMPONENT_ALIAS_KEYS",
    "PROJECT_STATE_COMPONENT_KEYS",
    "PROJECT_STATE_COMPONENT_SOURCES",
    "ProjectStateComponentsRepository",
    "extract_project_state_components",
    "merge_project_state_components",
    "strip_project_state_components",
]
