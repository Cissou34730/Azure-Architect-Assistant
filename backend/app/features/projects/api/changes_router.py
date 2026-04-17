"""Pending change-set endpoints owned by the projects feature."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.projects.api._deps import get_pending_changes_service_dep
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

_CANONICAL_CHANGE_COLLECTION_PATH = "/projects/{project_id}/pending-changes"
_LEGACY_CHANGE_COLLECTION_PATH = "/projects/{project_id}/changes"
_REVISE_DEFERRED_MESSAGE = (
    "Revise is deferred to v2. Use approve or reject for pending changes in v1."
)


@router.get(
    _LEGACY_CHANGE_COLLECTION_PATH,
    response_model=list[PendingChangeSetSummaryContract],
    include_in_schema=False,
)
@router.get(
    _CANONICAL_CHANGE_COLLECTION_PATH,
    response_model=list[PendingChangeSetSummaryContract],
)
async def list_project_changes(
    project_id: str,
    response: Response,
    status: Annotated[ChangeSetStatus | None, Query()] = None,
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
            status=status,
        )
    except ValueError as exc:
        raise map_value_error(exc, default_status=404) from exc


@router.get(
    f"{_LEGACY_CHANGE_COLLECTION_PATH}/{{change_set_id}}",
    response_model=PendingChangeSetContract,
    include_in_schema=False,
)
@router.get(
    f"{_CANONICAL_CHANGE_COLLECTION_PATH}/{{change_set_id}}",
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
    f"{_LEGACY_CHANGE_COLLECTION_PATH}/{{change_set_id}}/approve",
    response_model=ChangeSetReviewResultContract,
    include_in_schema=False,
)
@router.post(
    f"{_CANONICAL_CHANGE_COLLECTION_PATH}/{{change_set_id}}/approve",
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
        raise HTTPException(
            status_code=409,
            detail={"message": str(exc), "conflicts": exc.conflicts},
        ) from exc
    except ValueError as exc:
        raise map_value_error(exc, default_status=404) from exc


@router.post(
    f"{_LEGACY_CHANGE_COLLECTION_PATH}/{{change_set_id}}/reject",
    response_model=ChangeSetReviewResultContract,
    include_in_schema=False,
)
@router.post(
    f"{_CANONICAL_CHANGE_COLLECTION_PATH}/{{change_set_id}}/reject",
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
    f"{_LEGACY_CHANGE_COLLECTION_PATH}/{{change_set_id}}/revise",
    include_in_schema=False,
)
async def revise_project_change(
    project_id: str,
    change_set_id: str,
    request: ChangeSetReviewRequest,
) -> None:
    del project_id, change_set_id, request
    raise HTTPException(status_code=410, detail=_REVISE_DEFERRED_MESSAGE)
