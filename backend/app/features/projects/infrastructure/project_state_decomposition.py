"""Composition helpers for decomposed ProjectState storage."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.projects.infrastructure.architecture_inputs_repository import (
    ProjectArchitectureInputsRepository,
    merge_architecture_inputs,
)
from app.features.projects.infrastructure.project_state_components_repository import (
    ProjectStateComponentsRepository,
    merge_project_state_components,
)

_architecture_inputs_repository = ProjectArchitectureInputsRepository()
_project_state_components_repository = ProjectStateComponentsRepository()


async def compose_project_state(
    *,
    project_id: str,
    state: Mapping[str, Any],
    db: AsyncSession,
    backfill_missing_components: bool = True,
) -> dict[str, Any]:
    """Overlay decomposed stores on top of the compatibility blob payload."""
    if backfill_missing_components:
        await _project_state_components_repository.backfill_missing_from_state(
            project_id=project_id,
            state=state,
            db=db,
        )

    architecture_inputs = await _architecture_inputs_repository.get_architecture_inputs(
        project_id=project_id,
        db=db,
    )
    merged_state = merge_architecture_inputs(state, architecture_inputs)

    components = await _project_state_components_repository.get_project_state_components(
        project_id=project_id,
        db=db,
    )
    return merge_project_state_components(merged_state, components)


async def sync_project_state(
    *,
    project_id: str,
    state: Mapping[str, Any],
    db: AsyncSession,
    replace_missing: bool,
    updated_at: str | None = None,
) -> dict[str, Any]:
    """Persist decomposed families and return the stripped compatibility blob."""
    stripped_state = await _architecture_inputs_repository.sync_from_state(
        project_id=project_id,
        state=state,
        db=db,
        replace_missing=replace_missing,
        updated_at=updated_at,
    )
    return await _project_state_components_repository.sync_from_state(
        project_id=project_id,
        state=stripped_state,
        db=db,
        replace_missing=replace_missing,
        updated_at=updated_at,
    )


__all__ = ["compose_project_state", "sync_project_state"]
