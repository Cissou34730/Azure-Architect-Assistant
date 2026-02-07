"""API endpoints for normalized project checklists."""

from __future__ import annotations

import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents_system.checklists.service import ChecklistService, get_checklist_service
from app.models.checklist import Checklist, ChecklistItem
from app.models.project import ProjectState
from app.projects_database import get_db
from app.routers.checklists.schemas import (
    ChecklistDetail,
    ChecklistItemDetail,
    ChecklistItemLatestEvaluation,
    ChecklistSummary,
    EvaluateItemRequest,
    EvaluateItemResponse,
    ProgressResponse,
    ResyncResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects/{project_id}/checklists", tags=["checklists"])


@router.get("", response_model=list[ChecklistSummary])
async def list_checklists(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    service: ChecklistService = Depends(get_checklist_service),
) -> list[ChecklistSummary]:
    """List normalized checklists for a project."""
    async def _fetch_checklists() -> list[Checklist]:
        result = await db.execute(
            select(Checklist)
            .where(Checklist.project_id == project_id)
            .options(selectinload(Checklist.items))
        )
        return list(result.scalars().all())

    checklists = await _fetch_checklists()
    if not checklists:
        # Bootstrap from template so existing projects immediately expose
        # checklist items and 0% completion baseline in the UI.
        await service.ensure_project_checklist(project_id)
        checklists = await _fetch_checklists()

    return [
        ChecklistSummary(
            id=checklist.id,
            project_id=checklist.project_id,
            template_id=checklist.template_id,
            template_slug=checklist.template_slug,
            title=checklist.title,
            version=checklist.version,
            status=checklist.status.value if hasattr(checklist.status, "value") else str(checklist.status),
            items_count=len(checklist.items),
            last_synced_at=checklist.updated_at,
        )
        for checklist in checklists
    ]


@router.get("/{checklist_id:uuid}", response_model=ChecklistDetail)
async def get_checklist_detail(
    project_id: str,
    checklist_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ChecklistDetail:
    """Get one checklist with item-level detail."""
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

    item_details: list[ChecklistItemDetail] = []
    for item in checklist.items:
        latest_eval = None
        if item.evaluations:
            latest_eval = max(item.evaluations, key=lambda e: e.created_at or checklist.updated_at)
        item_details.append(
            ChecklistItemDetail(
                id=item.id,
                template_item_id=item.template_item_id,
                title=item.title,
                description=item.description,
                pillar=item.pillar,
                severity=item.severity.value if hasattr(item.severity, "value") else str(item.severity),
                guidance=item.guidance,
                item_metadata=item.item_metadata,
                latest_evaluation=(
                    ChecklistItemLatestEvaluation(
                        status=latest_eval.status.value
                        if hasattr(latest_eval.status, "value")
                        else str(latest_eval.status),
                        evaluator=latest_eval.evaluator,
                        timestamp=latest_eval.created_at,
                    )
                    if latest_eval
                    else None
                ),
            )
        )

    return ChecklistDetail(
        id=checklist.id,
        project_id=checklist.project_id,
        template_id=checklist.template_id,
        template_slug=checklist.template_slug,
        title=checklist.title,
        version=checklist.version,
        status=checklist.status.value if hasattr(checklist.status, "value") else str(checklist.status),
        items_count=len(checklist.items),
        last_synced_at=checklist.updated_at,
        items=item_details,
    )


@router.post("/items/{item_id}/evaluate", response_model=EvaluateItemResponse)
async def evaluate_checklist_item(
    project_id: str,
    item_id: UUID,
    request: EvaluateItemRequest,
    service: ChecklistService = Depends(get_checklist_service),
) -> EvaluateItemResponse:
    """Create a manual evaluation for a checklist item."""
    try:
        evaluation = await service.evaluate_item(
            project_id=project_id,
            item_id=item_id,
            evaluation_payload=request.model_dump(exclude_none=True),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to evaluate checklist item %s: %s", item_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create checklist evaluation") from exc
    return EvaluateItemResponse(status="success", evaluation_id=str(evaluation.id))


@router.get("/progress", response_model=ProgressResponse)
async def get_checklist_progress(
    project_id: str,
    checklist_id: UUID | None = Query(default=None),
    service: ChecklistService = Depends(get_checklist_service),
) -> ProgressResponse:
    """Return progress metrics for checklist completion."""
    progress = await service.get_progress(project_id, checklist_id)
    next_actions = await service.list_next_actions(project_id, limit=10)
    return ProgressResponse(
        total_items=progress.get("total_items", 0),
        completed_items=progress.get("completed_items", 0),
        percent_complete=float(progress.get("percent_complete", 0)),
        severity_breakdown=progress.get("severity_breakdown", {}),
        status_breakdown=progress.get("status_breakdown", {}),
        next_actions=next_actions,
        last_updated=str(progress.get("last_updated", "")),
    )


@router.post("/resync", response_model=ResyncResponse)
async def resync_checklists_from_project_state(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    service: ChecklistService = Depends(get_checklist_service),
) -> ResyncResponse:
    """Force sync from ``ProjectState.state.wafChecklist`` into normalized tables."""
    state_obj = (
        await db.execute(select(ProjectState).where(ProjectState.project_id == project_id))
    ).scalar_one_or_none()
    if state_obj is None:
        raise HTTPException(status_code=404, detail="Project state not found")

    try:
        state_dict = json.loads(state_obj.state) if isinstance(state_obj.state, str) else state_obj.state
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid project state JSON") from exc

    result = await service.sync_project(project_id, state_dict)
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=f"Resync failed: {result.get('errors', ['unknown'])}")

    return ResyncResponse(
        status=result.get("status", "unknown"),
        items_synced=int(result.get("items_synced", 0)),
        evaluations_synced=int(result.get("evaluations_synced", 0)),
        errors=[str(e) for e in result.get("errors", [])],
    )
