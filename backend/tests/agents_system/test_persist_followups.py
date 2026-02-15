from app.agents_system.langgraph.nodes.persist import (
    _count_open_waf_items,
    _handle_waf_followup_guardrail,
    _select_new_uncovered_questions,
)


def test_select_new_uncovered_questions_dedup_and_budget() -> None:
    selected = _select_new_uncovered_questions(
        existing_questions=[
            "Topic 2 (Requirements): confirm NFRs",
            "Topic WAF: update checklist with evidence",
        ],
        uncovered_questions=[
            "Topic WAF: update checklist with evidence",
            "Topic 4 (Architecture): confirm style",
            "Topic 1 (Foundations): create C4 container",
            "Topic Cost: budget target",
        ],
        max_questions=2,
    )

    assert selected == [
        "Topic 4 (Architecture): confirm style",
        "Topic 1 (Foundations): create C4 container",
    ]


def test_count_open_waf_items_handles_latest_status() -> None:
    state = {
        "wafChecklist": {
            "items": [
                {"id": "1", "evaluations": [{"status": "covered"}]},
                {"id": "2", "evaluations": [{"status": "partial"}]},
                {"id": "3", "evaluations": [{"status": "notCovered"}]},
                {"id": "4", "evaluations": []},
            ]
        }
    }

    assert _count_open_waf_items(state) == 3


def test_waf_followup_guardrail_triggers_in_validate_stage_without_updates() -> None:
    state = {
        "wafChecklist": {
            "items": [
                {"id": "1", "evaluations": [{"status": "partial"}]},
                {"id": "2", "evaluations": [{"status": "covered"}]},
            ]
        }
    }

    result = _handle_waf_followup_guardrail(
        next_stage="validate",
        combined_updates={},
        updated_state=state,
        final_answer="base answer",
    )

    assert "WAF follow-up" in result
    assert "remaining open items: 1" in result


def test_waf_followup_guardrail_skips_when_waf_updated() -> None:
    state = {
        "wafChecklist": {
            "items": [
                {"id": "1", "evaluations": [{"status": "partial"}]},
            ]
        }
    }

    result = _handle_waf_followup_guardrail(
        next_stage="validate",
        combined_updates={"wafChecklist": {"items": [{"id": "1"}]}},
        updated_state=state,
        final_answer="base answer",
    )

    assert result == "base answer"
