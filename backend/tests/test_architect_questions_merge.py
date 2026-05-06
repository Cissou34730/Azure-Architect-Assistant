"""Tests for architect questions merge support in PendingChangesMergeService (Q2.5, Q2.6)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.features.projects.application.pending_changes_merge_service import (
    PendingChangesMergeService,
)
from app.features.projects.contracts import ChangeSetStatus, PendingChangeSetContract


def _make_change_set(patch: dict) -> PendingChangeSetContract:
    return PendingChangeSetContract(
        id="cs-aq-1",
        project_id="proj-1",
        stage="clarify",
        status=ChangeSetStatus.PENDING,
        created_at=datetime.now(timezone.utc).isoformat(),
        source_message_id="msg-aq-1",
        bundle_summary="Architect questions update",
        proposed_patch=patch,
        artifact_drafts=[],
    )


class TestArchitectQuestionsCreate:
    def test_create_new_architect_questions(self) -> None:
        service = PendingChangesMergeService()
        current_state: dict = {"architectQuestions": []}
        patch = {
            "_architectQuestions": {
                "items": [
                    {
                        "id": "aq-1",
                        "question": "Should we use zone-redundant storage?",
                        "theme": "Reliability",
                        "designDecision": "Storage tier selection",
                        "status": "open",
                    }
                ]
            }
        }
        merged = service.apply_approved_patch(
            current_state=current_state,
            change_set=_make_change_set(patch),
        )
        assert len(merged["architectQuestions"]) == 1
        assert merged["architectQuestions"][0]["id"] == "aq-1"
        assert merged["architectQuestions"][0]["question"] == "Should we use zone-redundant storage?"

    def test_create_assigns_id_when_missing(self) -> None:
        service = PendingChangesMergeService()
        current_state: dict = {}
        patch = {
            "_architectQuestions": {
                "items": [
                    {
                        "question": "Which identity provider should we use?",
                        "theme": "Security",
                        "designDecision": "Identity topology",
                        "status": "open",
                    }
                ]
            }
        }
        merged = service.apply_approved_patch(
            current_state=current_state,
            change_set=_make_change_set(patch),
        )
        assert len(merged["architectQuestions"]) == 1
        assert merged["architectQuestions"][0]["id"] != ""  # auto-generated id

    def test_create_initializes_empty_list_when_missing_from_state(self) -> None:
        service = PendingChangesMergeService()
        current_state: dict = {}  # no architectQuestions key
        patch = {
            "_architectQuestions": {
                "items": [
                    {
                        "id": "aq-new",
                        "question": "How will we handle auth?",
                        "theme": "Security",
                        "designDecision": "Auth mechanism",
                        "status": "open",
                    }
                ]
            }
        }
        merged = service.apply_approved_patch(
            current_state=current_state,
            change_set=_make_change_set(patch),
        )
        assert "architectQuestions" in merged
        assert len(merged["architectQuestions"]) == 1


class TestArchitectQuestionsUpdate:
    def test_update_existing_question_status_and_answer(self) -> None:
        service = PendingChangesMergeService()
        current_state: dict = {
            "architectQuestions": [
                {
                    "id": "aq-1",
                    "question": "Should we use zone-redundant storage?",
                    "theme": "Reliability",
                    "designDecision": "Storage tier",
                    "status": "open",
                    "answer": None,
                }
            ]
        }
        patch = {
            "_architectQuestions": {
                "items": [
                    {
                        "id": "aq-1",
                        "status": "answered",
                        "answer": "Yes, use ZRS for production blob storage.",
                        "answeredAt": "2024-01-15T10:00:00Z",
                        "answerSource": "architect-review",
                    }
                ]
            }
        }
        merged = service.apply_approved_patch(
            current_state=current_state,
            change_set=_make_change_set(patch),
        )
        questions = merged["architectQuestions"]
        assert len(questions) == 1
        q = questions[0]
        assert q["id"] == "aq-1"
        assert q["status"] == "answered"
        assert q["answer"] == "Yes, use ZRS for production blob storage."
        assert q["answeredAt"] == "2024-01-15T10:00:00Z"
        # Original fields preserved
        assert q["question"] == "Should we use zone-redundant storage?"
        assert q["designDecision"] == "Storage tier"

    def test_update_preserves_unrelated_fields(self) -> None:
        service = PendingChangesMergeService()
        current_state: dict = {
            "architectQuestions": [
                {
                    "id": "aq-1",
                    "question": "How will networking be segmented?",
                    "theme": "Networking",
                    "designDecision": "Network topology",
                    "coverageSources": [{"kind": "waf", "id": "waf-net-1"}],
                    "riskIfUnanswered": "Network breach risk",
                    "status": "open",
                }
            ]
        }
        patch = {
            "_architectQuestions": {
                "items": [{"id": "aq-1", "status": "deferred"}]
            }
        }
        merged = service.apply_approved_patch(
            current_state=current_state,
            change_set=_make_change_set(patch),
        )
        q = merged["architectQuestions"][0]
        assert q["status"] == "deferred"
        assert q["coverageSources"] == [{"kind": "waf", "id": "waf-net-1"}]
        assert q["riskIfUnanswered"] == "Network breach risk"


class TestArchitectQuestionsDedup:
    def test_dedup_prevents_duplicate_question_text(self) -> None:
        service = PendingChangesMergeService()
        current_state: dict = {
            "architectQuestions": [
                {
                    "id": "aq-existing",
                    "question": "Should we use zone-redundant storage?",
                    "theme": "Reliability",
                    "designDecision": "Storage tier",
                    "status": "open",
                }
            ]
        }
        patch = {
            "_architectQuestions": {
                "items": [
                    {
                        "id": "aq-duplicate",
                        "question": "Should we use zone-redundant storage?",  # same as existing
                        "theme": "Reliability",
                        "designDecision": "Storage tier",
                        "status": "open",
                    }
                ]
            }
        }
        merged = service.apply_approved_patch(
            current_state=current_state,
            change_set=_make_change_set(patch),
        )
        # Only the original should remain — duplicate not added
        assert len(merged["architectQuestions"]) == 1
        assert merged["architectQuestions"][0]["id"] == "aq-existing"

    def test_dedup_case_insensitive_normalization(self) -> None:
        service = PendingChangesMergeService()
        current_state: dict = {
            "architectQuestions": [
                {
                    "id": "aq-existing",
                    "question": "Should we use Zone-Redundant Storage?",
                    "status": "open",
                }
            ]
        }
        patch = {
            "_architectQuestions": {
                "items": [
                    {
                        "id": "aq-near-dup",
                        "question": "should we use zone-redundant storage?",  # lowercase variant
                        "status": "open",
                    }
                ]
            }
        }
        merged = service.apply_approved_patch(
            current_state=current_state,
            change_set=_make_change_set(patch),
        )
        assert len(merged["architectQuestions"]) == 1

    def test_distinct_questions_both_added(self) -> None:
        service = PendingChangesMergeService()
        current_state: dict = {
            "architectQuestions": [
                {
                    "id": "aq-1",
                    "question": "How will we handle auth tokens?",
                    "status": "open",
                }
            ]
        }
        patch = {
            "_architectQuestions": {
                "items": [
                    {
                        "id": "aq-2",
                        "question": "Which storage redundancy tier should we choose?",
                        "status": "open",
                    }
                ]
            }
        }
        merged = service.apply_approved_patch(
            current_state=current_state,
            change_set=_make_change_set(patch),
        )
        assert len(merged["architectQuestions"]) == 2


class TestArchitectQuestionsUpdatesKey:
    """Tests for the dedicated `updates` key — answer/status updates for existing questions."""

    def test_updates_applies_answer_and_status(self) -> None:
        service = PendingChangesMergeService()
        current_state: dict = {
            "architectQuestions": [
                {
                    "id": "aq-1",
                    "question": "Should we use zone-redundant storage?",
                    "theme": "Reliability",
                    "status": "open",
                    "answer": None,
                }
            ]
        }
        patch = {
            "_architectQuestions": {
                "updates": [
                    {
                        "id": "aq-1",
                        "status": "answered",
                        "answer": "Use zone-redundant storage.",
                        "answeredAt": "2024-01-15T10:00:00Z",
                        "answerSource": "architect",
                    }
                ]
            }
        }
        merged = service.apply_approved_patch(
            current_state=current_state,
            change_set=_make_change_set(patch),
        )
        q = merged["architectQuestions"][0]
        assert q["status"] == "answered"
        assert q["answer"] == "Use zone-redundant storage."
        assert q["answeredAt"] == "2024-01-15T10:00:00Z"
        assert q["answerSource"] == "architect"
        assert q["question"] == "Should we use zone-redundant storage?"

    def test_updates_deferred_status(self) -> None:
        service = PendingChangesMergeService()
        current_state: dict = {
            "architectQuestions": [
                {"id": "aq-2", "question": "Which region?", "status": "open"}
            ]
        }
        patch = {"_architectQuestions": {"updates": [{"id": "aq-2", "status": "deferred"}]}}
        merged = service.apply_approved_patch(current_state=current_state, change_set=_make_change_set(patch))
        assert merged["architectQuestions"][0]["status"] == "deferred"
        assert merged["architectQuestions"][0]["question"] == "Which region?"

    def test_updates_missing_id_raises(self) -> None:
        service = PendingChangesMergeService()
        patch = {"_architectQuestions": {"updates": [{"status": "answered"}]}}
        with pytest.raises(ValueError, match="must include an id"):
            service.apply_approved_patch(current_state={}, change_set=_make_change_set(patch))

    def test_updates_unknown_id_raises(self) -> None:
        service = PendingChangesMergeService()
        current_state: dict = {"architectQuestions": [{"id": "aq-1", "question": "Q?", "status": "open"}]}
        patch = {"_architectQuestions": {"updates": [{"id": "aq-unknown", "status": "answered"}]}}
        with pytest.raises(ValueError, match="not found"):
            service.apply_approved_patch(current_state=current_state, change_set=_make_change_set(patch))

    def test_updates_and_items_can_coexist(self) -> None:
        service = PendingChangesMergeService()
        current_state: dict = {
            "architectQuestions": [
                {"id": "aq-1", "question": "Existing question?", "status": "open"}
            ]
        }
        patch = {
            "_architectQuestions": {
                "items": [{"id": "aq-2", "question": "New question?", "status": "open"}],
                "updates": [{"id": "aq-1", "status": "answered", "answer": "Yes."}],
            }
        }
        merged = service.apply_approved_patch(current_state=current_state, change_set=_make_change_set(patch))
        questions = merged["architectQuestions"]
        assert len(questions) == 2
        answered = next(q for q in questions if q["id"] == "aq-1")
        added = next(q for q in questions if q["id"] == "aq-2")
        assert answered["status"] == "answered"
        assert added["question"] == "New question?"

    def test_updates_invalid_type_raises(self) -> None:
        service = PendingChangesMergeService()
        patch = {"_architectQuestions": {"updates": "not-a-list"}}
        with pytest.raises(ValueError):
            service.apply_approved_patch(current_state={}, change_set=_make_change_set(patch))


class TestArchitectQuestionsValidation:
    def test_invalid_command_payload_raises(self) -> None:
        service = PendingChangesMergeService()
        patch = {"_architectQuestions": "not-a-dict"}
        with pytest.raises(ValueError, match="must be an object"):
            service.apply_approved_patch(
                current_state={},
                change_set=_make_change_set(patch),
            )

    def test_invalid_items_type_raises(self) -> None:
        service = PendingChangesMergeService()
        patch = {"_architectQuestions": {"items": "not-a-list"}}
        with pytest.raises(ValueError):
            service.apply_approved_patch(
                current_state={},
                change_set=_make_change_set(patch),
            )

    def test_empty_items_noop(self) -> None:
        service = PendingChangesMergeService()
        current_state = {"architectQuestions": [{"id": "aq-1", "question": "Existing?", "status": "open"}]}
        patch = {"_architectQuestions": {"items": []}}
        merged = service.apply_approved_patch(
            current_state=current_state,
            change_set=_make_change_set(patch),
        )
        assert merged["architectQuestions"] == current_state["architectQuestions"]
