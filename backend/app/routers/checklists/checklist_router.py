"""
API endpoints for WAF checklist management.
"""

import logging
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents_system.checklists.service import ChecklistService, get_checklist_service
from app.core.app_settings import get_settings, AppSettings
from app.projects_database import get_db
from app.models.checklist import Checklist, ChecklistItem
from app.routers.checklists.schemas import (
    ChecklistSummary,
    ChecklistDetail,
    ChecklistItemDetail,
    EvaluateItemRequest,
    ProgressResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/projects/{project_id}/checklists",
    tags=["checklists"]
)

@router.get("", response_model=list[ChecklistSummary])
async def list_checklists(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    service: ChecklistService = Depends(get_checklist_service),
) -> list[ChecklistSummary]:
    """List all checklists for a project."""
    stmt = select(Checklist).where(Checklist.project_id == project_id)
    result = await db.execute(stmt)
    checklists = result.scalars().all()
    
    return [
        ChecklistSummary(
            id=c.id,
            project_id=c.project_id,
            template_id=c.template_id,
            title=c.title,
            status=c.status.value if hasattr(c.status, "value") else str(c.status),
            created_at=c.created_at,
            updated_at=c.updated_at
        )
        for c in checklists
    ]

@router.get("/progress", response_model=ProgressResponse)
async def get_progress(
    project_id: str,
    checklist_id: Optional[UUID] = Query(None),
    service: ChecklistService = Depends(get_checklist_service),
) -> ProgressResponse:
    """Get project WAF progress metrics."""
    progress = await service.get_progress(project_id, checklist_id)
    next_actions = await service.list_next_actions(project_id, limit=5)
    
    return ProgressResponse(
        total_items=progress["total_items"],
        completed_items=progress["completed_items"],
        percent_complete=progress["percent_complete"],
        severity_breakdown=progress["severity_breakdown"],
        last_updated=progress["last_updated"],
        next_actions=next_actions
    )

@router.get("/{checklist_id}", response_model=ChecklistDetail)
async def get_checklist(
    project_id: str,
    checklist_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ChecklistDetail:
    """Get detailed checklist view with items."""
    stmt = (
        select(Checklist)
        .where(Checklist.id == checklist_id)
        .where(Checklist.project_id == project_id)
        .options(selectinload(Checklist.items).selectinload(ChecklistItem.evaluations))
    )
    result = await db.execute(stmt)
    checklist = result.scalar_one_or_none()
    
    if not checklist:
        raise HTTPException(status_code=404, detail="Checklist not found")
    
    items_detail = []
    for item in checklist.items:
        latest_status = "not_started"
        last_eval_date = None
        if item.evaluations:
            latest_eval = sorted(item.evaluations, key=lambda x: x.created_at, reverse=True)[0]
            latest_status = latest_eval.status.value if hasattr(latest_eval.status, "value") else str(latest_eval.status)
            last_eval_date = latest_eval.created_at.isoformat() if latest_eval.created_at else None

        items_detail.append(ChecklistItemDetail(
            id=item.id,
            template_item_id=item.template_item_id,
            title=item.title,
            description=item.description,
            pillar=item.pillar,
            severity=item.severity.value if hasattr(item.severity, "value") else str(item.severity),
            latest_status=latest_status,
            last_evaluated=last_eval_date
        ))

    return ChecklistDetail(
        id=checklist.id,
        project_id=checklist.project_id,
        template_id=checklist.template_id,
        title=checklist.title,
        status=checklist.status.value if hasattr(checklist.status, "value") else str(checklist.status),
        items=items_detail
    )

@router.post("/items/{item_id}/evaluate")
async def evaluate_item(
    project_id: str,
    item_id: UUID,
    request: EvaluateItemRequest,
    service: ChecklistService = Depends(get_checklist_service),
):
    """Manually evaluate a checklist item."""
    try:
        evaluation = await service.evaluate_item(
            project_id=project_id,
            item_id=item_id,
            evaluation_payload=request.model_dump()
        )
        return {"status": "success", "evaluation_id": str(evaluation.id)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Manual evaluation failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
