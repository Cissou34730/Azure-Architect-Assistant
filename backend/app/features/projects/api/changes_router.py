"""Read-only pending change set endpoints owned by the projects feature."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.projects.application.pending_changes_merge_service import (
    PendingChangeConflictError,
)
from app.features.projects.application.pending_changes_service import (
    ProjectPendingChangesService,
)
from app.features.projects.contracts import (
    ChangeSetReviewRequest,
    ChangeSetReviewResultContract,
    ChangeSetStatus,
    PendingChangeSetContract,
    PendingChangeSetSummaryContract,
)
from app.shared.db.projects_database import get_db
from app.shared.http.error_utils import map_value_error

router = APIRouter(prefix="/api", tags=["projects"])


def get_pending_changes_service_dep() -> ProjectPendingChangesService:
    from ._deps import get_pending_changes_service_dep as _get_pending_changes_service_dep

    return _get_pending_changes_service_dep()


@dataclass(frozen=True)
class ChangesQueryParams:
    status: ChangeSetStatus | None = Query(default=None)


@router.get(
    "/projects/{project_id}/changes",
    response_model=list[PendingChangeSetSummaryContract],
)
async def list_project_changes(
    project_id: str,
    params: Annotated[ChangesQueryParams, Depends()],
    response: Response,
    db: AsyncSession = Depends(get_db),
    pending_changes_service: ProjectPendingChangesService = Depends(
        get_pending_changes_service_dep
    ),
) -> list[PendingChangeSetSummaryContract]:
    """List pending change sets projected from current project state."""
    del response
    try:
        return await pending_changes_service.list_pending_changes(
            project_id=project_id,
            db=db,
            status=params.status,
        )
    except ValueError as exc:
        raise map_value_error(exc, default_status=404) from exc


@router.get(
    "/projects/{project_id}/changes/{change_set_id}",
    response_model=PendingChangeSetContract,
)
async def get_project_change(
    project_id: str,
    change_set_id: str,
    db: AsyncSession = Depends(get_db),
    pending_changes_service: ProjectPendingChangesService = Depends(
        get_pending_changes_service_dep
    ),
) -> PendingChangeSetContract:
    """Return a single pending change set with its artifact drafts."""
    try:
        return await pending_changes_service.get_pending_change(
            project_id=project_id,
            change_set_id=change_set_id,
            db=db,
        )
    except ValueError as exc:
        raise map_value_error(exc, default_status=404) from exc


@router.post(
    "/projects/{project_id}/changes/{change_set_id}/approve",
    response_model=ChangeSetReviewResultContract,
)
async def approve_project_change(
    project_id: str,
    change_set_id: str,
    request: ChangeSetReviewRequest,
    db: AsyncSession = Depends(get_db),
    pending_changes_service: ProjectPendingChangesService = Depends(
        get_pending_changes_service_dep
    ),
) -> ChangeSetReviewResultContract:
    try:
        return await pending_changes_service.approve_pending_change(
            project_id=project_id,
            change_set_id=change_set_id,
            reason=request.reason,
            db=db,
        )
    except PendingChangeConflictError as exc:
        raise HTTPException(status_code=409, detail={"message": str(exc), "conflicts": exc.conflicts}) from exc
    except ValueError as exc:
        raise map_value_error(exc, default_status=404) from exc


@router.post(
    "/projects/{project_id}/changes/{change_set_id}/reject",
    response_model=ChangeSetReviewResultContract,
)
async def reject_project_change(
    project_id: str,
    change_set_id: str,
    request: ChangeSetReviewRequest,
    db: AsyncSession = Depends(get_db),
    pending_changes_service: ProjectPendingChangesService = Depends(
        get_pending_changes_service_dep
    ),
) -> ChangeSetReviewResultContract:
    try:
        return await pending_changes_service.reject_pending_change(
            project_id=project_id,
            change_set_id=change_set_id,
            reason=request.reason,
            db=db,
        )
    except ValueError as exc:
        raise map_value_error(exc, default_status=404) from exc


@router.post(
    "/projects/{project_id}/changes/{change_set_id}/revise",
    response_model=ChangeSetReviewResultContract,
)
async def revise_project_change(
    project_id: str,
    change_set_id: str,
    request: ChangeSetReviewRequest,
    db: AsyncSession = Depends(get_db),
    pending_changes_service: ProjectPendingChangesService = Depends(
        get_pending_changes_service_dep
    ),
) -> ChangeSetReviewResultContract:
    try:
        return await pending_changes_service.revise_pending_change(
            project_id=project_id,
            change_set_id=change_set_id,
            reason=request.reason,
            db=db,
        )
    except ValueError as exc:
        raise map_value_error(exc, default_status=404) from exc
