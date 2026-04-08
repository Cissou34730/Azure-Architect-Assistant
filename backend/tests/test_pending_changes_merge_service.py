from __future__ import annotations

from datetime import datetime, timezone

from app.features.projects.application.pending_changes_merge_service import (
    PendingChangesMergeService,
)
from app.features.projects.contracts import ChangeSetStatus, PendingChangeSetContract


def test_apply_approved_patch_merges_clarification_resolution_updates() -> None:
    service = PendingChangesMergeService()
    current_state = {
        "requirements": [
            {
                "id": "req-auth",
                "text": "Support partner sign-in",
                "category": "functional",
                "ambiguity": {"isAmbiguous": True, "notes": "Identity boundary is unclear."},
            }
        ],
        "clarificationQuestions": [
            {
                "id": "q-auth",
                "question": "Do partners use their own tenant or a shared tenant?",
                "status": "open",
                "relatedRequirementIds": ["req-auth"],
            }
        ],
        "assumptions": [],
    }
    change_set = PendingChangeSetContract(
        id="cs-clarify-1",
        project_id="proj-1",
        stage="clarify",
        status=ChangeSetStatus.PENDING,
        created_at=datetime.now(timezone.utc).isoformat(),
        source_message_id="msg-clarify-1",
        bundle_summary="Resolved clarification answers",
        proposed_patch={
            "_clarificationResolution": {
                "requirements": [
                    {
                        "id": "req-auth",
                        "text": "Support partner sign-in with Microsoft Entra B2B collaboration.",
                        "category": "functional",
                        "ambiguity": {"isAmbiguous": False, "notes": ""},
                    }
                ],
                "clarificationQuestions": [{"id": "q-auth", "status": "answered"}],
                "assumptions": [
                    {
                        "id": "assumption-1",
                        "text": "Partners authenticate from their own Microsoft Entra tenants.",
                        "status": "open",
                        "relatedRequirementIds": ["req-auth"],
                    }
                ],
            }
        },
        artifact_drafts=[],
    )

    merged_state = service.apply_approved_patch(
        current_state=current_state,
        change_set=change_set,
    )

    assert merged_state["requirements"] == [
        {
            "id": "req-auth",
            "text": "Support partner sign-in with Microsoft Entra B2B collaboration.",
            "category": "functional",
            "ambiguity": {"isAmbiguous": False, "notes": ""},
        }
    ]
    assert merged_state["clarificationQuestions"] == [
        {
            "id": "q-auth",
            "question": "Do partners use their own tenant or a shared tenant?",
            "status": "answered",
            "relatedRequirementIds": ["req-auth"],
        }
    ]
    assert merged_state["assumptions"] == [
        {
            "id": "assumption-1",
            "text": "Partners authenticate from their own Microsoft Entra tenants.",
            "status": "open",
            "relatedRequirementIds": ["req-auth"],
        }
    ]
