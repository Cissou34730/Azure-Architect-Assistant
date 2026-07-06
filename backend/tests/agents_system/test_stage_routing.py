from __future__ import annotations

import pytest

from app.agents_system.langgraph.nodes.stage_routing import classify_next_stage


@pytest.mark.asyncio
async def test_classify_next_stage_returns_typed_architecture_classification() -> None:
    result = await classify_next_stage(
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


@pytest.mark.asyncio
async def test_classify_next_stage_keeps_code_review_requests_out_of_iac() -> None:
    result = await classify_next_stage(
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


@pytest.mark.asyncio
async def test_classify_next_stage_routes_human_override_to_decision_capture() -> None:
    result = await classify_next_stage(
        {
            "user_message": "I accept the risk and override the multi-region recommendation for budget reasons.",
            "current_project_state": {
                "requirements": [{"id": "req-1", "text": "Keep monthly cost low"}],
                "candidateArchitectures": [{"id": "ca-1"}],
                "wafChecklist": {"items": []},
            },
        }
    )

    assert result["next_stage"] == "manage_adr"
    assert result["stage_classification"]["rationale"] == (
        "Detected human architect override or accepted-risk intent requiring decision/risk capture."
    )


@pytest.mark.asyncio
async def test_state_gap_does_not_route_to_cost_or_iac_without_user_intent() -> None:
    result = await classify_next_stage(
        {
            "user_message": "What should I focus on next?",
            "current_project_state": {
                "requirements": [{"id": "req-1", "text": "Host on Azure"}],
                "candidateArchitectures": [{"id": "ca-1"}],
                "adrs": [{"id": "adr-1"}],
                "findings": [{"id": "finding-1"}],
                "wafChecklist": {"items": [{"id": "waf-1"}]},
            },
        }
    )

    assert result["next_stage"] == "general"
    assert result["stage_classification"] == {
        "stage": "general",
        "confidence": 0.55,
        "source": "state_gaps",
        "rationale": "No unresolved architecture decision was detected from state alone; keep the next response advisory.",
    }
