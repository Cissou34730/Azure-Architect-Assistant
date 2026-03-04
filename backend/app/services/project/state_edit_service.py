"""Project state mutation helpers extracted from router handlers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProjectState


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

        result = await db.execute(
            select(ProjectState).where(ProjectState.project_id == project_id)
        )
        state_record = result.scalar_one_or_none()
        if not state_record:
            raise HTTPException(status_code=404, detail="Project state not found")

        state = json.loads(state_record.state)
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

        state_record.state = json.dumps(state)
        state_record.updated_at = datetime.now(timezone.utc).isoformat()
        await db.commit()
        return state

