"""API endpoints for normalized project checklists."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents_system.checklists.service import ChecklistService, get_checklist_service
from app.core.app_settings import get_app_settings
from app.projects_database import get_db
from app.routers.checklists.schemas import (
    ChecklistDetail,
    ChecklistSummary,
    EvaluateItemRequest,
    EvaluateItemResponse,
    ProgressResponse,
)
from app.routers.error_utils import map_value_error
from app.services.checklists_api_service import ChecklistsApiService

router = APIRouter(prefix="/api/projects/{project_id}/checklists", tags=["checklists"])

_checklists_api_service = ChecklistsApiService()


def get_checklists_api_service_dep() -> ChecklistsApiService:
    return _checklists_api_service


@router.get("", response_model=list[ChecklistSummary])
async def list_checklists(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    service: ChecklistService = Depends(get_checklist_service),
    checklists_api_service: ChecklistsApiService = Depends(get_checklists_api_service_dep),
) -> list[ChecklistSummary]:
    """List normalized checklists for a project."""
    payload = await checklists_api_service.list_checklists(
        project_id=project_id,
        db=db,
        checklist_service=service,
    )
    return [ChecklistSummary.model_validate(item) for item in payload]


@router.get("/{checklist_id:uuid}", response_model=ChecklistDetail)
async def get_checklist_detail(
    project_id: str,
    checklist_id: UUID,
    db: AsyncSession = Depends(get_db),
    checklists_api_service: ChecklistsApiService = Depends(get_checklists_api_service_dep),
) -> ChecklistDetail:
    """Get one checklist with item-level detail."""
    payload = await checklists_api_service.get_checklist_detail(
        project_id=project_id,
        checklist_id=checklist_id,
        db=db,
    )
    return ChecklistDetail.model_validate(payload)


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
        raise map_value_error(exc, default_status=404) from exc
    return EvaluateItemResponse(status="success", evaluation_id=str(evaluation.id))


@router.get("/progress", response_model=ProgressResponse)
async def get_checklist_progress(
    project_id: str,
    checklist_id: UUID | None = Query(default=None),
    service: ChecklistService = Depends(get_checklist_service),
) -> ProgressResponse:
    """Return progress metrics for checklist completion."""
    progress = await service.get_progress(project_id, checklist_id)
    next_actions = await service.list_next_actions(project_id, limit=get_app_settings().checklist_next_actions_limit)
    return ProgressResponse(
        total_items=progress.get("total_items", 0),
        completed_items=progress.get("completed_items", 0),
        percent_complete=float(progress.get("percent_complete", 0)),
        severity_breakdown=progress.get("severity_breakdown", {}),
        status_breakdown=progress.get("status_breakdown", {}),
        next_actions=next_actions,
        last_updated=str(progress.get("last_updated", "")),
    )

