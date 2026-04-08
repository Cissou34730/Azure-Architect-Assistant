import pytest

from app.agents_system.langgraph.nodes.agent_native import _build_system_directives
from app.agents_system.langgraph.nodes.research import (
    build_research_plan_node,
    execute_research_worker_node,
)


@pytest.mark.asyncio
async def test_build_research_plan_returns_non_blocking_mindmap_guidance() -> None:
    state = {
        "next_stage": "clarify",
        "mindmap_coverage": {
            "topics": {
                "security": {"status": "not-addressed"},
                "reliability": {"status": "not-addressed"},
                "cost": {"status": "addressed"},
            }
        },
        "current_project_state": {},
    }

    result = await build_research_plan_node(state)

    guidance = result.get("mindmap_guidance")
    assert isinstance(guidance, dict)
    assert guidance.get("non_blocking") is True
    assert guidance.get("mode") == "advisory"
    assert guidance.get("priority") == "high"
    assert guidance.get("focus_topics") == ["security", "reliability"]


def test_system_directives_prioritize_mindmap_in_discovery() -> None:
    state = {
        "next_stage": "clarify",
        "stage_directives": "Stage directives section",
        "research_plan": ["one", "two"],
        "mindmap_guidance": {
            "focus_topics": ["security", "reliability"],
            "suggested_prompts": ["p1", "p2"],
        },
        "mindmap_coverage": {"topics": {}},
    }

    directives = _build_system_directives(state)

    mindmap_index = directives.find("### Mind map advisory guidance")
    stage_index = directives.find("### Stage directives")
    assert mindmap_index != -1
    assert stage_index != -1
    assert mindmap_index < stage_index


def test_system_directives_prioritize_stage_in_validation() -> None:
    state = {
        "next_stage": "validate",
        "stage_directives": "Validation stage directives",
        "research_plan": ["one"],
        "mindmap_guidance": {
            "focus_topics": ["security"],
            "suggested_prompts": ["p1"],
        },
        "mindmap_coverage": {"topics": {}},
    }

    directives = _build_system_directives(state)

    stage_index = directives.find("### Stage directives")
    mindmap_index = directives.find("### Mind map advisory guidance")
    assert stage_index != -1
    assert mindmap_index != -1
    assert stage_index < mindmap_index
    assert "checklist status updates and persistence rules take priority" in directives


@pytest.mark.asyncio
async def test_execute_research_worker_skips_when_plan_is_missing() -> None:
    result = await execute_research_worker_node(
        {
            "next_stage": "propose_candidate",
            "research_plan": [],
            "current_project_state": {},
        }
    )

    artifact = result.get("research_execution_artifact")
    assert artifact == {
        "status": "skipped",
        "reason": "no_research_plan",
        "stage": "propose_candidate",
        "packets_created": 0,
    }
    assert result.get("research_evidence_packets") == []


def test_system_directives_prefer_research_packets_over_raw_plan() -> None:
    state = {
        "next_stage": "propose_candidate",
        "stage_directives": "Architecture directives",
        "research_plan": ["raw plan that should not be rendered"],
        "research_evidence_packets": [
            {
                "packet_id": "packet-1",
                "focus": "Front Door reliability guidance",
                "query": "Azure Front Door reliability zone redundancy",
                "recommended_sources": ["Azure Architecture Center"],
            }
        ],
        "mindmap_guidance": None,
        "mindmap_coverage": {"topics": {}},
    }

    directives = _build_system_directives(state)

    assert "### Research evidence packets" in directives
    assert "packet-1" in directives
    assert "Azure Front Door reliability zone redundancy" in directives
    assert "### Research plan (run MCP searches/fetches for these)" not in directives
