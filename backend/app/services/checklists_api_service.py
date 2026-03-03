"""Service layer for checklist router read/resync operations."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.checklist import Checklist, ChecklistItem
from app.models.project import ProjectState


def _enum_str(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


class ChecklistsApiService:
    """Encapsulates checklist query and projection logic for API responses."""

    async def list_checklists(
        self,
        *,
        project_id: str,
        db: AsyncSession,
        checklist_service: Any,
    ) -> list[dict[str, Any]]:
        await checklist_service.ensure_project_checklists(project_id)
        result = await db.execute(
            select(Checklist)
            .where(Checklist.project_id == project_id)
            .options(selectinload(Checklist.items))
        )
        checklists = list(result.scalars().all())
        return [
            {
                "id": checklist.id,
                "project_id": checklist.project_id,
                "template_id": checklist.template_id,
                "template_slug": checklist.template_slug,
                "title": checklist.title,
                "version": checklist.version,
                "status": _enum_str(checklist.status),
                "items_count": len(checklist.items),
                "last_synced_at": checklist.updated_at,
            }
            for checklist in checklists
        ]

    async def get_checklist_detail(
        self,
        *,
        project_id: str,
        checklist_id: UUID,
        db: AsyncSession,
    ) -> dict[str, Any]:
        checklist = (
            await db.execute(
                select(Checklist)
                .where(Checklist.id == checklist_id)
                .where(Checklist.project_id == project_id)
                .options(selectinload(Checklist.items).selectinload(ChecklistItem.evaluations))
            )
        ).scalar_one_or_none()
        if checklist is None:
            raise HTTPException(status_code=404, detail="Checklist not found")

        items: list[dict[str, Any]] = []
        for item in checklist.items:
            latest_eval = None
            if item.evaluations:
                latest_eval = max(
                    item.evaluations, key=lambda e: e.created_at or checklist.updated_at
                )
            items.append(
                {
                    "id": item.id,
                    "template_item_id": item.template_item_id,
                    "title": item.title,
                    "description": item.description,
                    "pillar": item.pillar,
                    "severity": _enum_str(item.severity),
                    "guidance": item.guidance,
                    "item_metadata": item.item_metadata,
                    "latest_evaluation": (
                        {
                            "status": _enum_str(latest_eval.status),
                            "evaluator": latest_eval.evaluator,
                            "timestamp": latest_eval.created_at,
                        }
                        if latest_eval
                        else None
                    ),
                }
            )

        return {
            "id": checklist.id,
            "project_id": checklist.project_id,
            "template_id": checklist.template_id,
            "template_slug": checklist.template_slug,
            "title": checklist.title,
            "version": checklist.version,
            "status": _enum_str(checklist.status),
            "items_count": len(checklist.items),
            "last_synced_at": checklist.updated_at,
            "items": items,
        }

    async def resync_from_project_state(
        self,
        *,
        project_id: str,
        db: AsyncSession,
        checklist_service: Any,
    ) -> dict[str, Any]:
        state_obj = (
            await db.execute(select(ProjectState).where(ProjectState.project_id == project_id))
        ).scalar_one_or_none()
        if state_obj is None:
            raise HTTPException(status_code=404, detail="Project state not found")
        try:
            state_dict = (
                json.loads(state_obj.state)
                if isinstance(state_obj.state, str)
                else state_obj.state
            )
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Invalid project state JSON") from exc

        result = await checklist_service.sync_project(project_id, state_dict)
        if result.get("status") == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Resync failed: {result.get('errors', ['unknown'])}",
            )
        return {
            "status": result.get("status", "unknown"),
            "items_synced": int(result.get("items_synced", 0)),
            "evaluations_synced": int(result.get("evaluations_synced", 0)),
            "errors": [str(e) for e in result.get("errors", [])],
        }

