"""Service for recording architect question answers as pending changes."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Literal, Protocol

from app.features.projects.contracts import ChangeSetStatus, PendingChangeSetContract


ArchitectQuestionAnswerStatus = Literal["answered", "deferred", "not_applicable"]


class PendingChangeRecorder(Protocol):
    async def record_pending_change(
        self,
        *,
        project_id: str,
        change_set: PendingChangeSetContract,
        db: object,
    ) -> PendingChangeSetContract: ...


class ArchitectQuestionAnswerService:
    """Records an architect question answer as an approval-first pending change."""

    def __init__(
        self,
        *,
        pending_change_recorder: PendingChangeRecorder,
        change_set_id_factory: Callable[[], str] | None = None,
        now_factory: Callable[[], str] | None = None,
    ) -> None:
        self._pending_change_recorder = pending_change_recorder
        self._change_set_id_factory = change_set_id_factory or (lambda: str(uuid.uuid4()))
        self._now_factory = now_factory or (
            lambda: datetime.now(timezone.utc).isoformat()
        )

    async def record_answer(
        self,
        *,
        project_id: str,
        question_id: str,
        answer: str | None,
        status: ArchitectQuestionAnswerStatus,
        answer_source: str | None = None,
        db: object,
    ) -> PendingChangeSetContract:
        """Create a pending change that updates an architect question's answer and status."""
        answered_at = self._now_factory()
        change_set_id = self._change_set_id_factory()

        proposed_patch = {
            "_architectQuestions": {
                "updates": [
                    {
                        "id": question_id,
                        "status": status,
                        "answer": answer,
                        "answeredAt": answered_at,
                        "answerSource": answer_source or "architect",
                    }
                ]
            }
        }

        change_set = PendingChangeSetContract(
            id=change_set_id,
            project_id=project_id,
            stage="architect_questions",
            status=ChangeSetStatus.PENDING,
            created_at=answered_at,
            bundle_summary=f"Architect question '{question_id}' marked as {status}.",
            proposed_patch=proposed_patch,
            artifact_drafts=[],
        )

        return await self._pending_change_recorder.record_pending_change(
            project_id=project_id,
            change_set=change_set,
            db=db,
        )
