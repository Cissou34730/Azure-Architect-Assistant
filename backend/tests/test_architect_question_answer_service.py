"""Unit tests for ArchitectQuestionAnswerService (Q3.4)."""

from __future__ import annotations

import pytest

from app.features.agent.application.architect_question_answer_service import (
    ArchitectQuestionAnswerService,
)
from app.features.projects.contracts import ChangeSetStatus, PendingChangeSetContract


class _PendingChangeRecorderStub:
    def __init__(self) -> None:
        self.recorded_change_set: PendingChangeSetContract | None = None

    async def record_pending_change(
        self,
        *,
        project_id: str,
        change_set: PendingChangeSetContract,
        db: object,
    ) -> PendingChangeSetContract:
        self.recorded_change_set = change_set
        return change_set


@pytest.mark.asyncio
async def test_record_answer_creates_pending_change_with_correct_patch() -> None:
    recorder = _PendingChangeRecorderStub()
    service = ArchitectQuestionAnswerService(
        pending_change_recorder=recorder,
        change_set_id_factory=lambda: "cs-aq-answer-1",
    )

    result = await service.record_answer(
        project_id="proj-1",
        question_id="q-1",
        answer="Use zone-redundant storage",
        status="answered",
        db=object(),
    )

    assert result is not None
    assert recorder.recorded_change_set is not None
    cs = recorder.recorded_change_set
    assert cs.id == "cs-aq-answer-1"
    assert cs.project_id == "proj-1"
    assert cs.stage == "architect_questions"
    assert cs.status is ChangeSetStatus.PENDING

    updates = cs.proposed_patch["_architectQuestions"]["updates"]
    assert len(updates) == 1
    u = updates[0]
    assert u["id"] == "q-1"
    assert u["status"] == "answered"
    assert u["answer"] == "Use zone-redundant storage"
    assert u["answerSource"] == "architect"
    assert "answeredAt" in u


@pytest.mark.asyncio
async def test_record_answer_deferred_status() -> None:
    recorder = _PendingChangeRecorderStub()
    service = ArchitectQuestionAnswerService(pending_change_recorder=recorder)

    await service.record_answer(
        project_id="proj-1",
        question_id="q-2",
        answer=None,
        status="deferred",
        db=object(),
    )

    cs = recorder.recorded_change_set
    assert cs is not None
    u = cs.proposed_patch["_architectQuestions"]["updates"][0]
    assert u["status"] == "deferred"
    assert u["answer"] is None


@pytest.mark.asyncio
async def test_record_answer_not_applicable_with_custom_source() -> None:
    recorder = _PendingChangeRecorderStub()
    service = ArchitectQuestionAnswerService(pending_change_recorder=recorder)

    await service.record_answer(
        project_id="proj-2",
        question_id="q-3",
        answer="Out of scope for this engagement.",
        status="not_applicable",
        answer_source="tech-lead",
        db=object(),
    )

    cs = recorder.recorded_change_set
    assert cs is not None
    u = cs.proposed_patch["_architectQuestions"]["updates"][0]
    assert u["status"] == "not_applicable"
    assert u["answerSource"] == "tech-lead"


@pytest.mark.asyncio
async def test_record_answer_bundle_summary_describes_change() -> None:
    recorder = _PendingChangeRecorderStub()
    service = ArchitectQuestionAnswerService(pending_change_recorder=recorder)

    await service.record_answer(
        project_id="proj-1",
        question_id="q-4",
        answer="Yes",
        status="answered",
        db=object(),
    )

    cs = recorder.recorded_change_set
    assert cs is not None
    assert "q-4" in cs.bundle_summary or "answered" in cs.bundle_summary
