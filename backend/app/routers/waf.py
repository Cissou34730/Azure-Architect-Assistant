"""
API routes for WAF checklist management.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents_system.checklists.service import ChecklistService, get_checklist_service
from app.models.checklist import EvaluationStatus
from app.projects_database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects/{project_id}/waf", tags=["WAF"])

class WafEvaluationUpdate(BaseModel):
    status: EvaluationStatus
    evidence: dict[str, Any] | None = None
    score: float | None = None
    evaluator: str = "user"

class WafSyncResponse(BaseModel):
    status: str
    message: str
    count: int

@router.get("/checklist", response_model=dict[str, Any])
async def get_project_checklist(
    project_id: str,
    service: ChecklistService = Depends(get_checklist_service)
):
    """
    Get the WAF checklist for a project, including evaluations.
    """
    checklist = await service.engine.get_project_checklist(project_id, "waf-2024")
    if not checklist:
        # Try to instantiate if missing
        checklist = await service.initialize_project_checklist(project_id)
        if not checklist:
            raise HTTPException(status_code=404, detail="Project or WAF template not found")

    # Manually serialize to avoid depth issues or use a Pydantic schema
    # For now, return a simplified dict
    return {
        "id": str(checklist.id),
        "title": checklist.title,
        "status": checklist.status,
        "completionPercentage": checklist.completion_percentage,
        "items": [
            {
                "id": str(item.id),
                "title": item.title,
                "pillar": item.pillar,
                "severity": item.severity,
                "evaluation": {
                    "status": item.evaluations[0].status if item.evaluations else "not_started",
                    "evidence": item.evaluations[0].evidence if item.evaluations else None,
                    "updated_at": item.evaluations[0].updated_at if item.evaluations else None
                } if item.evaluations else None
            } for item in checklist.items
        ]
    }

@router.patch("/items/{item_id}")
async def update_waf_evaluation(
    project_id: str,
    item_id: str,
    update: WafEvaluationUpdate,
    service: ChecklistService = Depends(get_checklist_service)
):
    """
    Manual update of a Waf checklist item evaluation.
    """
    evaluation = await service.engine.update_item_evaluation(
        item_id=item_id,
        project_id=project_id,
        status=update.status.value if hasattr(update.status, 'value') else update.status,
        score=update.score or (1.0 if update.status == "fulfilled" else 0.0),
        evidence=update.evidence,
        evaluator=update.evaluator
    )

    # Recalculate progress
    checklist = await service.engine.get_project_checklist(project_id, "waf-2024")
    if checklist:
        await service.engine.calculate_progress(checklist.id)

    return {"status": "success", "new_completion": checklist.completion_percentage if checklist else 0.0}

@router.post("/sync", response_model=WafSyncResponse)
async def sync_legacy_waf(
    project_id: str,
    service: ChecklistService = Depends(get_checklist_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Force synchronization from legacy ProjectState.state to normalized tables.
    """
    from app.models.project import ProjectState
    from app.services.normalize_helpers import extract_waf_evaluations

    stmt = select(ProjectState).where(ProjectState.project_id == project_id)
    result = await db.execute(stmt)
    state_obj = result.scalar_one_or_none()

    if not state_obj or not state_obj.state:
        return WafSyncResponse(status="error", message="Project state not found", count=0)

    evals = extract_waf_evaluations(state_obj.state)
    if not evals:
         return WafSyncResponse(status="skipped", message="No legacy WAF data found", count=0)

    # Ensure checklist exists
    await service.initialize_project_checklist(project_id)

    count = 0
    for eval_data in evals:
        await service.engine.update_item_evaluation(
            item_id=eval_data["item_id"],
            project_id=project_id,
            status=eval_data["status"],
            evidence=eval_data["evidence"],
            evaluator="legacy-migration"
        )
        count += 1

    # Final progress recalculation
    checklist = await service.engine.get_project_checklist(project_id, "waf-2024")
    if checklist:
        await service.engine.calculate_progress(checklist.id)

    return WafSyncResponse(status="success", message="Sync complete", count=count)
