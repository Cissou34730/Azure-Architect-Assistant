from __future__ import annotations

from app.agents_system.services.iteration_logging import (
    derive_mcp_query_updates_from_steps,
    derive_uncovered_topic_questions,
)


class _Action:
    def __init__(self, tool: str, tool_input):
        self.tool = tool
        self.tool_input = tool_input


def test_derive_mcp_query_updates_from_steps_records_urls() -> None:
    steps = [
        (
            _Action("microsoft_docs_search", {"query": "Azure WAF reliability"}),
            "Found 2 results\n\n1. Title\n   URL: https://learn.microsoft.com/azure/well-architected/\n",
        )
    ]

    updates = derive_mcp_query_updates_from_steps(
        intermediate_steps=steps, user_message="help with architecture"
    )
    assert "mcpQueries" in updates
    assert len(updates["mcpQueries"]) == 1
    assert updates["mcpQueries"][0]["queryText"] == "Azure WAF reliability"
    assert updates["mcpQueries"][0]["resultUrls"] == [
        "https://learn.microsoft.com/azure/well-architected/"
    ]


def test_derive_uncovered_topic_questions_limits_to_three() -> None:
    questions = derive_uncovered_topic_questions(
        {
            "requirements": [],
            "candidateArchitectures": [],
            "diagrams": [],
            "wafChecklist": {},
            "iacArtifacts": [],
            "costEstimates": [],
        }
    )
    assert len(questions) <= 3
    assert all(isinstance(q, str) and q for q in questions)
