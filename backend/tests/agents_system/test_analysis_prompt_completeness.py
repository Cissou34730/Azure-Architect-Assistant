"""Tests for improved document analysis prompt.

Verifies the analyze_documents prompt captures comprehensive requirements
with full scope, sources, and ambiguity flags.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.services.llm_service import LLMService


class TestAnalysisPromptCompleteness:
    """Verify the analysis system prompt captures all critical extraction areas."""

    def _get_analysis_system_prompt(self) -> str:
        """Extract the system prompt used by analyze_documents."""
        # The prompt is defined inline in LLMService.analyze_documents;
        # We verify it contains the expected extraction directives.
        import inspect
        source = inspect.getsource(LLMService.analyze_documents)
        return source

    def test_prompt_requests_exhaustive_requirements(self) -> None:
        source = self._get_analysis_system_prompt()
        assert "exhaustive" in source.lower() or "comprehensive" in source.lower() or "thorough" in source.lower()

    def test_prompt_requests_stakeholder_extraction(self) -> None:
        source = self._get_analysis_system_prompt()
        assert "stakeholder" in source.lower()

    def test_prompt_requests_integration_extraction(self) -> None:
        source = self._get_analysis_system_prompt()
        assert "integration" in source.lower()

    def test_prompt_requests_explicit_implicit_requirements(self) -> None:
        source = self._get_analysis_system_prompt()
        assert "implicit" in source.lower()

    def test_prompt_requests_priority(self) -> None:
        source = self._get_analysis_system_prompt()
        assert "priority" in source.lower()

    def test_prompt_requests_user_volumes(self) -> None:
        source = self._get_analysis_system_prompt()
        assert "volume" in source.lower() or "scale" in source.lower() or "concurrent" in source.lower()

    def test_prompt_requests_document_cross_reference(self) -> None:
        source = self._get_analysis_system_prompt()
        assert "cross-reference" in source.lower() or "cross reference" in source.lower() or "documentid" in source.lower()
