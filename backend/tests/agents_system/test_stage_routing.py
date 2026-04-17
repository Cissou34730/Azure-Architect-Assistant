from __future__ import annotations

from app.agents_system.langgraph.nodes.stage_routing import classify_next_stage


def test_classify_next_stage_returns_typed_architecture_classification() -> None:
    result = classify_next_stage(
        {
            "user_message": "Design the architecture for a multi-region Azure workload.",
            "current_project_state": {
                "requirements": [{"id": "req-1", "text": "Support active-active regions"}],
            },
        }
    )

    assert result["next_stage"] == "propose_candidate"
    assert result["stage_classification"] == {
        "stage": "propose_candidate",
        "confidence": 0.95,
        "source": "intent_rules",
        "rationale": "Matched architecture-design intent keywords in the user message.",
    }


def test_classify_next_stage_keeps_code_review_requests_out_of_iac() -> None:
    result = classify_next_stage(
        {
            "user_message": "Please code review the ADR before we approve it.",
            "current_project_state": {},
        }
    )

    assert result["next_stage"] == "general"
    assert result["stage_classification"] == {
        "stage": "general",
        "confidence": 0.88,
        "source": "intent_rules",
        "rationale": "Detected review-oriented wording without IaC-specific generation intent.",
    }
