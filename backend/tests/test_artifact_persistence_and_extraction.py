"""Tests for artifact persistence directive injection and extraction depth.

Covers:
- Issue 1: artifact_edit_detected as separate graph state field
- Issue 1: _build_system_directives injects mandatory artifact-update directive
- Issue 1: MCP guardrail exempted for artifact-edit turns
- Issue 2: chat_max_agent_iterations setting configurable via AppSettings
- Issue 2: general-stage context pack includes document summaries
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Issue 1: stage routing — artifact_edit_detected as graph state field
# ---------------------------------------------------------------------------


class TestArtifactEditDetection:
    """Verify stage classification emits artifact_edit_detected in state."""

    def test_artifact_edit_intent_sets_state_flag(self) -> None:
        from app.agents_system.langgraph.nodes.stage_routing import classify_next_stage

        state = {
            "user_message": "please update the requirements and assumptions based on the input documents",
            "current_project_state": {},
            "agent_output": "",
        }
        result = classify_next_stage(state)
        assert result["artifact_edit_detected"] is True

    def test_no_artifact_edit_intent_omits_flag(self) -> None:
        from app.agents_system.langgraph.nodes.stage_routing import classify_next_stage

        state = {
            "user_message": "what is the current architecture?",
            "current_project_state": {"requirements": [{"id": "r1", "text": "need HA"}]},
            "agent_output": "",
        }
        result = classify_next_stage(state)
        assert result.get("artifact_edit_detected", False) is False

    def test_artifact_edit_confidence_is_high(self) -> None:
        from app.agents_system.langgraph.nodes.stage_routing import classify_next_stage

        state = {
            "user_message": "update the requirements based on the documents",
            "current_project_state": {},
            "agent_output": "",
        }
        result = classify_next_stage(state)
        classification = result["stage_classification"]
        assert classification["confidence"] >= 0.92

    # --- Creation/generation verbs (NEW: addresses verb coverage gap) ---

    @pytest.mark.parametrize(
        "message",
        [
            "can you also state some clarification questions",
            "states some clarification questions",
            "add requirements based on the input documents",
            "create assumptions from the uploaded files",
            "generate clarification questions for this project",
            "suggest some requirements",
            "propose assumptions based on the design",
            "extract requirements from the uploaded documents",
            "come up with clarification questions",
        ],
    )
    def test_creation_verbs_trigger_artifact_edit(self, message: str) -> None:
        from app.agents_system.langgraph.nodes.stage_routing import classify_next_stage

        state = {
            "user_message": message,
            "current_project_state": {},
            "agent_output": "",
        }
        result = classify_next_stage(state)
        assert result["artifact_edit_detected"] is True, (
            f"Expected artifact_edit_detected=True for: {message!r}"
        )

    @pytest.mark.parametrize(
        "message",
        [
            "what services do you suggest?",
            "can you create a quick overview?",
            "propose an approach",
            "generate a summary of the project",
        ],
    )
    def test_creation_verbs_without_artifact_target_no_trigger(self, message: str) -> None:
        from app.agents_system.langgraph.nodes.stage_routing import classify_next_stage

        state = {
            "user_message": message,
            "current_project_state": {},
            "agent_output": "",
        }
        result = classify_next_stage(state)
        assert result.get("artifact_edit_detected", False) is False, (
            f"Should NOT trigger artifact_edit for: {message!r}"
        )


# ---------------------------------------------------------------------------
# Issue: anti-inline guardrail in directives
# ---------------------------------------------------------------------------


class TestAntiInlineGuardrail:
    """Verify system directives include anti-inline guardrail when artifact_edit detected."""

    def test_anti_inline_directive_present_when_artifact_edit(self) -> None:
        from app.agents_system.langgraph.nodes.agent_native import _build_system_directives

        state = {
            "next_stage": "general",
            "user_message": "generate requirements",
            "artifact_edit_detected": True,
            "stage_classification": {
                "stage": "general",
                "confidence": 0.95,
                "source": "intent_rules",
                "rationale": "artifact edit",
            },
        }
        directives = _build_system_directives(state)
        directives_lower = directives.lower()
        assert "never" in directives_lower and "inline" in directives_lower, (
            "Should contain anti-inline directive forbidding inline diagrams/code"
        )

    def test_anti_inline_directive_mentions_diagrams_and_questions(self) -> None:
        from app.agents_system.langgraph.nodes.agent_native import _build_system_directives

        state = {
            "next_stage": "general",
            "user_message": "add clarification questions",
            "artifact_edit_detected": True,
        }
        directives = _build_system_directives(state)
        directives_lower = directives.lower()
        # Should mention both diagrams and clarification questions
        assert "diagram" in directives_lower
        assert "clarification" in directives_lower or "question" in directives_lower


# ---------------------------------------------------------------------------
# Issue 1: _build_system_directives — mandatory artifact update directive
# ---------------------------------------------------------------------------


class TestArtifactUpdateDirectiveInjection:
    """Verify system directives include mandatory artifact-update instruction."""

    def test_artifact_edit_directive_present_when_flagged(self) -> None:
        from app.agents_system.langgraph.nodes.agent_native import _build_system_directives

        state = {
            "next_stage": "general",
            "user_message": "update the requirements",
            "artifact_edit_detected": True,
            "stage_classification": {
                "stage": "general",
                "confidence": 0.95,
                "source": "intent_rules",
                "rationale": "artifact edit",
            },
        }
        directives = _build_system_directives(state)
        assert "MUST" in directives
        assert "aaa_" in directives

    def test_artifact_edit_directive_absent_when_not_flagged(self) -> None:
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
        # Should NOT have the forced artifact directive section header
        assert "### Artifact persistence override" not in directives

    def test_mcp_guardrail_relaxed_for_artifact_edit(self) -> None:
        from app.agents_system.langgraph.nodes.agent_native import _build_system_directives

        state = {
            "next_stage": "general",
            "user_message": "update the requirements",
            "artifact_edit_detected": True,
        }
        directives = _build_system_directives(state)
        # When artifact-edit is active, the MCP "always search before answer"
        # guardrail should be relaxed to not block persistence
        assert "persistence takes priority over research" in directives.lower() or \
               "persist first" in directives.lower() or \
               "do NOT require MCP" in directives


# ---------------------------------------------------------------------------
# Issue 2: chat_max_agent_iterations configurable
# ---------------------------------------------------------------------------


class TestMaxAgentIterationsConfigurable:
    """Verify MAX_AGENT_ITERATIONS reads from settings."""

    def test_default_max_iterations_is_15(self) -> None:
        from app.shared.config.settings.llm_tuning import LLMTuningSettingsMixin

        settings = LLMTuningSettingsMixin()
        assert settings.chat_max_agent_iterations == 15

    def test_get_max_agent_iterations_returns_setting(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.agents_system.langgraph import state as state_module

        class FakeSettings:
            chat_max_agent_iterations = 25

        monkeypatch.setattr(state_module, "get_app_settings", lambda: FakeSettings())
        assert state_module.get_max_agent_iterations() == 25


# ---------------------------------------------------------------------------
# Issue 2: general-stage context pack includes document summaries
# ---------------------------------------------------------------------------


class TestGeneralContextPackDocSummaries:
    """Verify context pack for general stage includes document summaries."""

    def test_general_pack_includes_document_titles(self) -> None:
        from app.agents_system.memory.context_packs.stage_packers import build_general_sections

        state = {
            "requirements": [{"id": "r1", "text": "need HA"}],
            "assumptions": [{"id": "a1", "text": "single region"}],
            "referenceDocuments": [
                {"id": "d1", "title": "Architecture Design.pdf", "summary": "Overview of the system"},
                {"id": "d2", "title": "NFR Spec.docx", "summary": "Non-functional requirements"},
            ],
        }
        sections = build_general_sections(state)
        combined = "\n".join(s.content for s in sections)
        assert "Architecture Design.pdf" in combined
        assert "NFR Spec.docx" in combined

    def test_general_pack_without_documents_still_works(self) -> None:
        from app.agents_system.memory.context_packs.stage_packers import build_general_sections

        state = {
            "requirements": [],
            "assumptions": [],
        }
        sections = build_general_sections(state)
        assert isinstance(sections, list)

    def test_general_stage_registered_in_service(self) -> None:
        from app.agents_system.memory.context_packs.service import _STAGE_REGISTRY

        assert "general" in _STAGE_REGISTRY
