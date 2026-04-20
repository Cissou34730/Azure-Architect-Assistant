"""Tests for context and iteration budget improvements.

Slice 3 of systemic quality improvements:
- Context budget raised from 12K to 24K tokens
- Document summary priority raised from 4 to 2
- Document summary truncation raised from 200 to 500 chars
- Agent iteration budget raised from 15 to 30
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Context budget default
# ---------------------------------------------------------------------------

class TestContextBudget:
    """Verify default context budget is raised."""

    def test_default_context_budget_24k(self) -> None:
        from app.shared.config.settings.agents import AgentsSettingsMixin
        m = AgentsSettingsMixin()
        assert m.aaa_context_max_budget_tokens == 24000

    def test_budget_still_configurable(self) -> None:
        from app.shared.config.settings.agents import AgentsSettingsMixin
        m = AgentsSettingsMixin(aaa_context_max_budget_tokens=32000)
        assert m.aaa_context_max_budget_tokens == 32000


# ---------------------------------------------------------------------------
# Document summary priority
# ---------------------------------------------------------------------------

class TestDocumentSummaryPriority:
    """Verify document summaries have raised priority."""

    def test_document_summary_priority_is_2(self) -> None:
        from app.agents_system.memory.context_packs.stage_packers import (
            _build_document_summaries_section,
        )
        state = {
            "referenceDocuments": [
                {"title": "Test Doc", "summary": "A test document summary"}
            ]
        }
        section = _build_document_summaries_section(state)
        assert section.priority == 2

    def test_empty_docs_still_priority_2(self) -> None:
        from app.agents_system.memory.context_packs.stage_packers import (
            _build_document_summaries_section,
        )
        section = _build_document_summaries_section({})
        assert section.priority == 2


# ---------------------------------------------------------------------------
# Document summary truncation
# ---------------------------------------------------------------------------

class TestDocumentSummaryTruncation:
    """Verify document summaries are truncated at 500 chars, not 200."""

    def test_summary_preserves_up_to_500_chars(self) -> None:
        from app.agents_system.memory.context_packs.stage_packers import (
            _build_document_summaries_section,
        )
        long_summary = "A" * 500
        state = {
            "referenceDocuments": [
                {"title": "Test Doc", "summary": long_summary}
            ]
        }
        section = _build_document_summaries_section(state)
        # Full 500-char summary should be in content
        assert "A" * 500 in section.content

    def test_summary_truncates_beyond_500_chars(self) -> None:
        from app.agents_system.memory.context_packs.stage_packers import (
            _build_document_summaries_section,
        )
        long_summary = "B" * 600
        state = {
            "referenceDocuments": [
                {"title": "Test Doc", "summary": long_summary}
            ]
        }
        section = _build_document_summaries_section(state)
        # Should NOT contain full 600-char summary
        assert "B" * 600 not in section.content
        # But should contain 500 chars worth
        assert "B" * 500 in section.content


# ---------------------------------------------------------------------------
# Agent iteration budget
# ---------------------------------------------------------------------------

class TestAgentIterationBudget:
    """Verify default iteration budget is raised."""

    def test_default_iterations_30(self) -> None:
        from app.shared.config.settings.llm_tuning import LLMTuningSettingsMixin
        m = LLMTuningSettingsMixin()
        assert m.chat_max_agent_iterations == 30

    def test_legacy_constant_updated(self) -> None:
        from app.agents_system.langgraph.state import MAX_AGENT_ITERATIONS
        assert MAX_AGENT_ITERATIONS == 30

    def test_iterations_still_configurable(self) -> None:
        from app.shared.config.settings.llm_tuning import LLMTuningSettingsMixin
        m = LLMTuningSettingsMixin(chat_max_agent_iterations=50)
        assert m.chat_max_agent_iterations == 50
