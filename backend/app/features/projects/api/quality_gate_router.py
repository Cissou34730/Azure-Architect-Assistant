"""Quality gate reporting endpoints owned by the projects feature."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.projects.application.quality_gate_service import QualityGateService
from app.features.projects.contracts import QualityGateReportContract
from app.shared.db.projects_database import get_db
from app.shared.http.error_utils import map_value_error

from ._deps import get_quality_gate_service_dep

router = APIRouter(prefix="/api", tags=["projects"])


@router.get(
    "/projects/{project_id}/quality-gate",
    response_model=QualityGateReportContract,
)
async def get_quality_gate(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    quality_gate_service: QualityGateService = Depends(get_quality_gate_service_dep),
) -> QualityGateReportContract:
    try:
        return await quality_gate_service.get_report(project_id=project_id, db=db)
    except ValueError as exc:
        raise map_value_error(exc, default_status=404) from exc
