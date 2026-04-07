"""Project state mutation helpers extracted from router handlers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.projects.infrastructure.project_state_decomposition import (
    compose_project_state,
)
from app.features.projects.infrastructure.project_state_store import ProjectStateStore

_project_state_store = ProjectStateStore()


class ProjectStateEditService:
    """Applies targeted, validated mutations to project state."""

    async def append_to_adr(
        self,
        *,
        project_id: str,
        adr_id: str,
        adr_field: str,
        append_text: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        field = (adr_field or "").strip()
        if field not in {"context", "decision", "consequences", "title"}:
            raise HTTPException(status_code=400, detail=f"Unsupported adrField: {field}")

        blob_state = await _project_state_store.get_blob_state(project_id=project_id, db=db)
        if blob_state is None:
            raise HTTPException(status_code=404, detail="Project state not found")

        state = await compose_project_state(
            project_id=project_id,
            state=blob_state,
            db=db,
        )
        adrs = state.get("adrs")
        if not isinstance(adrs, list):
            raise HTTPException(status_code=400, detail="No ADRs present in state")

        target = None
        for adr in adrs:
            if isinstance(adr, dict) and str(adr.get("id")) == adr_id:
                target = adr
                break
        if target is None:
            raise HTTPException(status_code=404, detail="ADR not found")

        text = (append_text or "").strip()
        if not text:
            raise HTTPException(status_code=400, detail="appendText is required")

        existing_val = str(target.get(field) or "").rstrip()
        target[field] = (existing_val + "\n" if existing_val else "") + text

        updated_at = datetime.now(timezone.utc).isoformat()
        await _project_state_store.persist_composed_state(
            project_id=project_id,
            state=state,
            db=db,
            replace_missing=False,
            updated_at=updated_at,
        )
        await db.commit()
        return state

