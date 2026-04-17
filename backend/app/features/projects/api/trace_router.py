"""Project trace timeline endpoints owned by the projects feature."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.projects.application.trace_service import ProjectTraceService
from app.features.projects.contracts.trace import ProjectTraceEventsResponse
from app.shared.db.projects_database import get_db
from app.shared.http.error_utils import map_value_error

from ._deps import get_trace_service_dep

router = APIRouter(prefix="/api", tags=["projects"])


@router.get("/projects/{project_id}/trace", response_model=ProjectTraceEventsResponse)
async def get_project_trace(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    trace_service: ProjectTraceService = Depends(get_trace_service_dep),
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
    thread_id: str | None = Query(default=None, alias="thread_id"),
) -> ProjectTraceEventsResponse:
    try:
        return await trace_service.list_events(
            project_id=project_id,
            db=db,
            limit=limit,
            thread_id=thread_id,
        )
    except ValueError as exc:
        raise map_value_error(exc, default_status=404) from exc
