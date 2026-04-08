from __future__ import annotations

from typing import Any

import pytest

from app.features.agent.application.clarification_resolution_worker import (
    ClarificationResolutionWorker,
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
async def test_resolve_and_record_pending_change_creates_reviewable_bundle() -> None:
    recorder = _PendingChangeRecorderStub()
    captured_input: dict[str, Any] = {}

    async def _resolver(resolution_input: dict[str, Any]) -> dict[str, Any]:
        captured_input.update(resolution_input)
        return {
            "summary": "Resolved identity and recovery clarifications from the latest user reply.",
            "requirementUpdates": [
                {
                    "requirementId": "req-auth",
                    "text": "Support partner sign-in with Microsoft Entra B2B collaboration.",
                    "category": "functional",
                    "answerSummary": "Partners authenticate with their own Microsoft Entra tenants.",
                    "relatedQuestionIds": ["q-auth"],
                },
                {
                    "requirementId": "req-dr",
                    "text": "Support disaster recovery with a 4-hour recovery time objective.",
                    "category": "nfr",
                    "answerSummary": "Production recovery must complete within four hours.",
                    "relatedQuestionIds": ["q-dr"],
                },
            ],
            "questionUpdates": [
                {
                    "questionId": "q-auth",
                    "status": "answered",
                    "answerSummary": "Partners authenticate with their own Microsoft Entra tenants.",
                    "relatedRequirementIds": ["req-auth"],
                },
                {
                    "questionId": "q-dr",
                    "status": "answered",
                    "answerSummary": "Production recovery must complete within four hours.",
                    "relatedRequirementIds": ["req-dr"],
                },
            ],
            "assumptions": [
                {
                    "text": "Partners are onboarded from their own Microsoft Entra tenants.",
                    "relatedRequirementIds": ["req-auth"],
                }
            ],
        }

    worker = ClarificationResolutionWorker(
        resolver=_resolver,
        pending_change_recorder=recorder,
        change_set_id_factory=lambda: "cs-clarify-1",
        artifact_id_factory=iter(
            [
                "artifact-req-auth",
                "artifact-req-dr",
                "artifact-question-auth",
                "artifact-question-dr",
                "artifact-assumption-1",
            ]
        ).__next__,
        assumption_id_factory=lambda: "assumption-1",
        now_factory=lambda: "2026-04-08T12:00:00+00:00",
    )

    change_set = await worker.resolve_and_record_pending_change(
        project_id="proj-1",
        user_message=(
            "Partners will use their own Entra tenants, and the production platform needs "
            "a 4-hour RTO."
        ),
        project_state={
            "requirements": [
                {
                    "id": "req-auth",
                    "text": "Support partner sign-in",
                    "category": "functional",
                    "ambiguity": {"isAmbiguous": True, "notes": "Identity boundary is unclear."},
                },
                {
                    "id": "req-dr",
                    "text": "Support business continuity",
                    "category": "nfr",
                    "ambiguity": {"isAmbiguous": True, "notes": "Recovery target is missing."},
                },
            ],
            "clarificationQuestions": [
                {
                    "id": "q-auth",
                    "question": "Do partners authenticate with your tenant or their own tenant?",
                    "status": "open",
                    "priority": 1,
                    "relatedRequirementIds": ["req-auth"],
                },
                {
                    "id": "q-dr",
                    "question": "What recovery time objective is required for production?",
                    "status": "open",
                    "priority": 2,
                    "relatedRequirementIds": ["req-dr"],
                },
            ],
            "assumptions": [
                {
                    "id": "assumption-existing",
                    "text": "Existing baseline assumption",
                    "status": "open",
                    "relatedRequirementIds": [],
                }
            ],
        },
        source_message_id="msg-clarify-1",
        db=object(),
    )

    assert captured_input["userMessage"].startswith("Partners will use their own Entra tenants")
    assert [question["id"] for question in captured_input["openClarificationQuestions"]] == [
        "q-auth",
        "q-dr",
    ]
    assert change_set.id == "cs-clarify-1"
    assert change_set.stage == "clarify"
    assert change_set.status is ChangeSetStatus.PENDING
    assert change_set.bundle_summary == "Resolved identity and recovery clarifications from the latest user reply."
    resolution_patch = change_set.proposed_patch["_clarificationResolution"]
    assert resolution_patch["requirements"] == [
        {
            "id": "req-auth",
            "text": "Support partner sign-in with Microsoft Entra B2B collaboration.",
            "category": "functional",
            "ambiguity": {"isAmbiguous": False, "notes": ""},
        },
        {
            "id": "req-dr",
            "text": "Support disaster recovery with a 4-hour recovery time objective.",
            "category": "nfr",
            "ambiguity": {"isAmbiguous": False, "notes": ""},
        },
    ]
    assert resolution_patch["clarificationQuestions"] == [
        {"id": "q-auth", "status": "answered"},
        {"id": "q-dr", "status": "answered"},
    ]
    assert resolution_patch["assumptions"] == [
        {
            "id": "assumption-1",
            "text": "Partners are onboarded from their own Microsoft Entra tenants.",
            "status": "open",
            "relatedRequirementIds": ["req-auth"],
        }
    ]
    assert [draft.artifact_type.value for draft in change_set.artifact_drafts] == [
        "requirement",
        "requirement",
        "clarification_question",
        "clarification_question",
        "assumption",
    ]
    assert recorder.recorded_change_set is not None


@pytest.mark.asyncio
async def test_resolve_and_record_pending_change_requires_actionable_updates() -> None:
    async def _resolver(_: dict[str, Any]) -> dict[str, Any]:
        return {
            "summary": "No changes",
            "requirementUpdates": [],
            "questionUpdates": [],
            "assumptions": [],
        }

    worker = ClarificationResolutionWorker(
        resolver=_resolver,
        pending_change_recorder=_PendingChangeRecorderStub(),
    )

    with pytest.raises(ValueError, match="no actionable clarification updates"):
        await worker.resolve_and_record_pending_change(
            project_id="proj-1",
            user_message="We should keep talking.",
            project_state={
                "clarificationQuestions": [
                    {
                        "id": "q-open-1",
                        "question": "What recovery time objective is required?",
                        "status": "open",
                    }
                ]
            },
            db=object(),
        )
