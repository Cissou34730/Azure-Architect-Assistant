"""Persistence helpers for the ProjectState compatibility blob."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.projects.infrastructure.project_state_decomposition import sync_project_state
from app.models.project import ProjectState


class ProjectStateStore:
    """Owns reads and writes of the legacy ProjectState compatibility blob."""

    async def get_record(self, *, project_id: str, db: AsyncSession) -> ProjectState | None:
        result = await db.execute(
            select(ProjectState).where(ProjectState.project_id == project_id)
        )
        return result.scalar_one_or_none()

    async def get_blob_state(self, *, project_id: str, db: AsyncSession) -> dict[str, Any] | None:
        record = await self.get_record(project_id=project_id, db=db)
        if record is None:
            return None
        return json.loads(record.state)

    async def ensure_record(
        self,
        *,
        project_id: str,
        db: AsyncSession,
        updated_at: str | None = None,
    ) -> ProjectState:
        record = await self.get_record(project_id=project_id, db=db)
        if record is not None:
            return record

        timestamp = updated_at or datetime.now(timezone.utc).isoformat()
        record = ProjectState(project_id=project_id, state=json.dumps({}), updated_at=timestamp)
        db.add(record)
        await db.flush()
        return record

    async def persist_composed_state(
        self,
        *,
        project_id: str,
        state: Mapping[str, Any],
        db: AsyncSession,
        replace_missing: bool,
        updated_at: str | None = None,
    ) -> dict[str, Any]:
        timestamp = updated_at or datetime.now(timezone.utc).isoformat()
        stripped_state = await sync_project_state(
            project_id=project_id,
            state=state,
            db=db,
            replace_missing=replace_missing,
            updated_at=timestamp,
        )
        record = await self.ensure_record(project_id=project_id, db=db, updated_at=timestamp)
        record.state = json.dumps(stripped_state)
        record.updated_at = timestamp
        return stripped_state


__all__ = ["ProjectStateStore"]
