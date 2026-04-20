"""Tests for LLM-based artifact intent classification.

Covers:
- Intent classifier returns correct results for artifact-intent messages
- Intent classifier returns no-intent for non-artifact messages
- Fallback on LLM errors returns safe default
- Keyword fast-path skips LLM call
- classify_next_stage async integration with LLM fallback
- Always-on output discipline in base guardrails
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest


# ---------------------------------------------------------------------------
# IntentClassifier unit tests
# ---------------------------------------------------------------------------


class TestIntentClassifier:
    """Verify LLM-based artifact intent classification."""

    @pytest.mark.asyncio
    async def test_detects_artifact_creation_intent(self) -> None:
        from app.agents_system.langgraph.nodes.intent_classifier import (
            ArtifactIntentResult,
            classify_artifact_intent,
        )

        mock_response = AsyncMock()
        mock_response.content = json.dumps(
            {"intent": True, "types": ["clarification_question"]}
        )

        with patch(
            "app.agents_system.langgraph.nodes.intent_classifier.get_ai_service"
        ) as mock_ai:
            mock_ai.return_value.chat = AsyncMock(return_value=mock_response)
            result = await classify_artifact_intent(
                "can you also state some clarification questions"
            )

        assert isinstance(result, ArtifactIntentResult)
        assert result.intent is True
        assert "clarification_question" in result.types

    @pytest.mark.asyncio
    async def test_detects_no_artifact_intent(self) -> None:
        from app.agents_system.langgraph.nodes.intent_classifier import (
            ArtifactIntentResult,
            classify_artifact_intent,
        )

        mock_response = AsyncMock()
        mock_response.content = json.dumps({"intent": False, "types": []})

        with patch(
            "app.agents_system.langgraph.nodes.intent_classifier.get_ai_service"
        ) as mock_ai:
            mock_ai.return_value.chat = AsyncMock(return_value=mock_response)
            result = await classify_artifact_intent("what is the current architecture?")

        assert isinstance(result, ArtifactIntentResult)
        assert result.intent is False
        assert result.types == []

    @pytest.mark.asyncio
    async def test_returns_safe_default_on_llm_error(self) -> None:
        from app.agents_system.langgraph.nodes.intent_classifier import (
            ArtifactIntentResult,
            classify_artifact_intent,
        )

        with patch(
            "app.agents_system.langgraph.nodes.intent_classifier.get_ai_service"
        ) as mock_ai:
            mock_ai.return_value.chat = AsyncMock(side_effect=Exception("LLM timeout"))
            result = await classify_artifact_intent("add some requirements")

        assert isinstance(result, ArtifactIntentResult)
        assert result.intent is False
        assert result.types == []

    @pytest.mark.asyncio
    async def test_returns_safe_default_on_malformed_json(self) -> None:
        from app.agents_system.langgraph.nodes.intent_classifier import (
            classify_artifact_intent,
        )

        mock_response = AsyncMock()
        mock_response.content = "not valid json at all"

        with patch(
            "app.agents_system.langgraph.nodes.intent_classifier.get_ai_service"
        ) as mock_ai:
            mock_ai.return_value.chat = AsyncMock(return_value=mock_response)
            result = await classify_artifact_intent("generate requirements")

        assert result.intent is False

    @pytest.mark.asyncio
    async def test_uses_system_message_not_user_interpolation(self) -> None:
        """Verify the classifier sends a system message (not user-interpolated prompt)."""
        from app.agents_system.langgraph.nodes.intent_classifier import (
            classify_artifact_intent,
        )

        mock_response = AsyncMock()
        mock_response.content = json.dumps({"intent": False, "types": []})

        with patch(
            "app.agents_system.langgraph.nodes.intent_classifier.get_ai_service"
        ) as mock_ai:
            mock_ai.return_value.chat = AsyncMock(return_value=mock_response)
            await classify_artifact_intent("test message")

            call_args = mock_ai.return_value.chat.call_args
            messages = call_args.kwargs.get("messages") or call_args[1].get("messages") or call_args[0][0]
            roles = [m.role if hasattr(m, "role") else m["role"] for m in messages]
            assert "system" in roles, "Should use a system message for classification"
            assert "user" in roles, "Should have a separate user message"

    @pytest.mark.asyncio
    async def test_uses_cheap_token_budget(self) -> None:
        """Verify the classifier uses low max_tokens for cost efficiency."""
        from app.agents_system.langgraph.nodes.intent_classifier import (
            classify_artifact_intent,
        )

        mock_response = AsyncMock()
        mock_response.content = json.dumps({"intent": False, "types": []})

        with patch(
            "app.agents_system.langgraph.nodes.intent_classifier.get_ai_service"
        ) as mock_ai:
            mock_ai.return_value.chat = AsyncMock(return_value=mock_response)
            await classify_artifact_intent("test message")

            call_args = mock_ai.return_value.chat.call_args
            max_tokens = call_args.kwargs.get("max_tokens")
            assert max_tokens is not None and max_tokens <= 128, (
                f"Should use cheap token budget, got {max_tokens}"
            )


# ---------------------------------------------------------------------------
# classify_next_stage async integration with LLM fallback
# ---------------------------------------------------------------------------


class TestClassifyNextStageWithLLMFallback:
    """Verify async classify_next_stage uses keyword fast-path + LLM fallback."""

    @pytest.mark.asyncio
    async def test_keyword_match_skips_llm_call(self) -> None:
        """When keywords match, LLM classifier should NOT be called."""
        from app.agents_system.langgraph.nodes.stage_routing import classify_next_stage

        with patch(
            "app.agents_system.langgraph.nodes.stage_routing.classify_artifact_intent"
        ) as mock_llm:
            state = {
                "user_message": "update the requirements based on the documents",
                "current_project_state": {},
                "agent_output": "",
            }
            result = await classify_next_stage(state)
            mock_llm.assert_not_called()
            assert result["artifact_edit_detected"] is True

    @pytest.mark.asyncio
    async def test_llm_fallback_when_keywords_miss(self) -> None:
        """When keywords don't match, LLM classifier should be called."""
        from app.agents_system.langgraph.nodes.intent_classifier import (
            ArtifactIntentResult,
        )
        from app.agents_system.langgraph.nodes.stage_routing import classify_next_stage

        llm_result = ArtifactIntentResult(intent=True, types=["clarification_question"])

        with patch(
            "app.agents_system.langgraph.nodes.stage_routing.classify_artifact_intent",
            new_callable=AsyncMock,
            return_value=llm_result,
        ) as mock_llm:
            state = {
                "user_message": "please provide me with clarification questions",
                "current_project_state": {},
                "agent_output": "",
            }
            result = await classify_next_stage(state)
            mock_llm.assert_called_once()
            assert result["artifact_edit_detected"] is True

    @pytest.mark.asyncio
    async def test_llm_failure_falls_back_to_no_intent(self) -> None:
        """When LLM fails, should safely default to no artifact intent."""
        from app.agents_system.langgraph.nodes.stage_routing import classify_next_stage

        with patch(
            "app.agents_system.langgraph.nodes.stage_routing.classify_artifact_intent",
            new_callable=AsyncMock,
            side_effect=Exception("provider timeout"),
        ):
            state = {
                "user_message": "provide me with some clarification questions",
                "current_project_state": {},
                "agent_output": "",
            }
            result = await classify_next_stage(state)
            assert result.get("artifact_edit_detected", False) is False


# ---------------------------------------------------------------------------
# Always-on output discipline in base guardrails
# ---------------------------------------------------------------------------


class TestAlwaysOnOutputDiscipline:
    """Verify base guardrails include anti-raw-markup rule regardless of artifact_edit."""

    def test_base_guardrails_forbid_raw_diagrams(self) -> None:
        from app.agents_system.langgraph.nodes.agent_native import _build_system_directives

        state = {
            "next_stage": "general",
            "user_message": "what is the architecture?",
            "stage_classification": {
                "stage": "general",
                "confidence": 0.86,
                "source": "intent_rules",
                "rationale": "general chat",
            },
        }
        directives = _build_system_directives(state)
        directives_lower = directives.lower()
        assert "never" in directives_lower and "diagram" in directives_lower, (
            "Base guardrails should forbid raw diagram markup even without artifact_edit"
        )

    def test_artifact_edit_guardrails_also_forbid_raw_diagrams(self) -> None:
        from app.agents_system.langgraph.nodes.agent_native import _build_system_directives

        state = {
            "next_stage": "general",
            "user_message": "update the requirements",
            "artifact_edit_detected": True,
        }
        directives = _build_system_directives(state)
        directives_lower = directives.lower()
        assert "never" in directives_lower and "diagram" in directives_lower

    def test_base_guardrails_allow_summaries(self) -> None:
        """Base guardrails should NOT forbid summarizing existing artifacts."""
        from app.agents_system.langgraph.nodes.agent_native import _build_system_directives

        state = {
            "next_stage": "general",
            "user_message": "summarize the requirements",
            "stage_classification": {
                "stage": "general",
                "confidence": 0.86,
                "source": "intent_rules",
                "rationale": "general chat",
            },
        }
        directives = _build_system_directives(state)
        directives_lower = directives.lower()
        # Should NOT say "never summarize" or forbid discussing existing artifacts
        assert "never summarize" not in directives_lower
        assert "never discuss" not in directives_lower


# ---------------------------------------------------------------------------
# Settings for intent classifier
# ---------------------------------------------------------------------------


class TestIntentClassifierSettings:
    """Verify intent classifier settings exist in LLMTuningSettingsMixin."""

    def test_intent_classifier_max_tokens_default(self) -> None:
        from app.shared.config.settings.llm_tuning import LLMTuningSettingsMixin

        settings = LLMTuningSettingsMixin()
        assert hasattr(settings, "intent_classifier_max_tokens")
        assert settings.intent_classifier_max_tokens <= 128

    def test_intent_classifier_timeout_default(self) -> None:
        from app.shared.config.settings.llm_tuning import LLMTuningSettingsMixin

        settings = LLMTuningSettingsMixin()
        assert hasattr(settings, "intent_classifier_timeout_seconds")
        assert settings.intent_classifier_timeout_seconds <= 10.0
