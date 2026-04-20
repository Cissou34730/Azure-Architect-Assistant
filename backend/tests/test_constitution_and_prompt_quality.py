"""Tests for global constitution injection and prompt quality improvements.

Slice 1 of systemic quality improvements:
- Constitution YAML exists and is loaded by PromptLoader as first shared file
- Constitution directives appear in ALL agent prompt compositions
- Requirements extraction prompt uses "comprehensive" not "fewer"
- Agent prompts remove hard question caps
- Forced-final-answer directive tells agent to complete work, not deflect
- Guardrails allow decisive recommendations
- Base persona includes completeness mandate
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


# ---------------------------------------------------------------------------
# Constitution file existence and content
# ---------------------------------------------------------------------------

class TestConstitutionYAML:
    """Verify constitution.yaml exists with required directives."""

    def _prompts_dir(self) -> Path:
        return Path(__file__).parent.parent / "config" / "prompts"

    def test_constitution_file_exists(self) -> None:
        path = self._prompts_dir() / "constitution.yaml"
        assert path.exists(), "constitution.yaml must exist in config/prompts/"

    def test_constitution_has_system_prompt(self) -> None:
        path = self._prompts_dir() / "constitution.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert "system_prompt" in data, "constitution.yaml must have system_prompt key"
        prompt = data["system_prompt"]
        assert isinstance(prompt, str)
        assert len(prompt) > 50, "Constitution prompt must be substantive"

    def test_constitution_mandates_thoroughness(self) -> None:
        path = self._prompts_dir() / "constitution.yaml"
        prompt = yaml.safe_load(path.read_text(encoding="utf-8"))["system_prompt"].lower()
        assert "thorough" in prompt or "comprehensive" in prompt or "exhaustive" in prompt

    def test_constitution_mandates_completeness(self) -> None:
        path = self._prompts_dir() / "constitution.yaml"
        prompt = yaml.safe_load(path.read_text(encoding="utf-8"))["system_prompt"].lower()
        assert "complete" in prompt

    def test_constitution_mandates_decisiveness(self) -> None:
        path = self._prompts_dir() / "constitution.yaml"
        prompt = yaml.safe_load(path.read_text(encoding="utf-8"))["system_prompt"].lower()
        assert "recommend" in prompt or "decisive" in prompt

    def test_constitution_does_not_encourage_deflection(self) -> None:
        path = self._prompts_dir() / "constitution.yaml"
        prompt = yaml.safe_load(path.read_text(encoding="utf-8"))["system_prompt"].lower()
        assert "ask before" not in prompt
        assert "fewer" not in prompt


# ---------------------------------------------------------------------------
# PromptLoader composes constitution as FIRST shared file
# ---------------------------------------------------------------------------

class TestConstitutionInPromptLoader:
    """Verify PromptLoader includes constitution in all prompt compositions."""

    def test_constitution_in_shared_prompt_files(self) -> None:
        from app.agents_system.config.prompt_loader import _SHARED_PROMPT_FILES
        assert "constitution.yaml" in _SHARED_PROMPT_FILES
        assert _SHARED_PROMPT_FILES[0] == "constitution.yaml", \
            "constitution.yaml must be the FIRST shared prompt file"

    def test_compose_prompt_includes_constitution_for_orchestrator(self) -> None:
        from app.agents_system.config.prompt_loader import PromptLoader
        loader = PromptLoader()
        composed = loader.compose_prompt(
            agent_type="orchestrator",
            stage="general",
            context_budget=0,
        )
        assert "thorough" in composed.lower() or "comprehensive" in composed.lower() or "exhaustive" in composed.lower()

    def test_compose_prompt_includes_constitution_for_stage_worker(self) -> None:
        from app.agents_system.config.prompt_loader import PromptLoader
        loader = PromptLoader()
        composed = loader.compose_prompt(
            agent_type="requirements_extractor",
            stage="extract_requirements",
            context_budget=0,
        )
        # Constitution should appear in ALL paths, including stage workers
        assert "thorough" in composed.lower() or "comprehensive" in composed.lower() or "exhaustive" in composed.lower()

    def test_constitution_appears_before_other_prompts(self) -> None:
        from app.agents_system.config.prompt_loader import PromptLoader
        loader = PromptLoader()
        composed = loader.compose_prompt(
            agent_type="orchestrator",
            stage="general",
            context_budget=0,
        )
        # Constitution content should appear before persona content
        constitution_idx = composed.lower().find("constitution")
        if constitution_idx == -1:
            # If word "constitution" isn't in the prompt, check for the key concept
            constitution_idx = composed.lower().find("thoroughness")
            if constitution_idx == -1:
                constitution_idx = composed.lower().find("completeness")
        persona_idx = composed.lower().find("role")
        # Constitution must appear before the role section (base_persona)
        assert constitution_idx < persona_idx, \
            "Constitution directives must appear before base persona"


# ---------------------------------------------------------------------------
# Requirements extraction prompt: comprehensive not conservative
# ---------------------------------------------------------------------------

class TestRequirementsExtractionPrompt:
    """Verify requirements extraction no longer uses anti-completeness language."""

    def _load_prompt(self) -> str:
        path = Path(__file__).parent.parent / "config" / "prompts" / "requirements_extraction.yaml"
        return yaml.safe_load(path.read_text(encoding="utf-8"))["system_prompt"].lower()

    def test_no_fewer_well_supported(self) -> None:
        prompt = self._load_prompt()
        assert "fewer" not in prompt, \
            "requirements_extraction.yaml must not say 'fewer' — use 'comprehensive'"

    def test_no_conservative_extraction(self) -> None:
        prompt = self._load_prompt()
        assert "conservatively" not in prompt, \
            "Must not mandate conservative reading — use thorough reading"

    def test_comprehensive_extraction(self) -> None:
        prompt = self._load_prompt()
        assert "comprehensive" in prompt or "thorough" in prompt, \
            "Must mandate comprehensive/thorough extraction"

    def test_source_grounding_preserved(self) -> None:
        """Ensure we keep source citation requirements (rubber-duck finding)."""
        prompt = self._load_prompt()
        assert "citation" in prompt or "source" in prompt or "excerpt" in prompt


# ---------------------------------------------------------------------------
# Agent prompts: remove deflection patterns
# ---------------------------------------------------------------------------

class TestAgentPromptsDeflection:
    """Verify agent_prompts.yaml no longer has deflection patterns."""

    def _load_prompt(self) -> str:
        path = Path(__file__).parent.parent / "config" / "prompts" / "agent_prompts.yaml"
        return yaml.safe_load(path.read_text(encoding="utf-8"))["system_prompt"]

    def test_no_hard_question_caps(self) -> None:
        prompt = self._load_prompt()
        assert "10–12 total" not in prompt, \
            "Hard question cap of 10-12 total must be removed"
        assert "10-12 total" not in prompt

    def test_allows_decisive_recommendations(self) -> None:
        """Agent should be allowed to RECOMMEND a preferred option."""
        prompt = self._load_prompt().lower()
        assert "must not select" not in prompt, \
            "'MUST NOT select' must be replaced with recommendation guidance"

    def test_proactive_not_contradicted(self) -> None:
        """Proactive and Ask Before Assuming must not directly conflict."""
        prompt = self._load_prompt()
        # "Ask Before Assuming" should be softened to "verify when uncertain"
        assert "If ANY are unclear, ASK SPECIFICALLY" not in prompt, \
            "'If ANY are unclear, ASK SPECIFICALLY' is too aggressive a gate"


# ---------------------------------------------------------------------------
# Forced-final-answer directive: complete work, don't deflect
# ---------------------------------------------------------------------------

class TestForcedFinalAnswerDirective:
    """Verify the forced-final-answer text tells agent to complete work."""

    def test_final_directive_does_not_deflect(self) -> None:
        from app.agents_system.langgraph.nodes.agent_native import (
            _run_streaming_agent_loop,
        )
        import inspect
        source = inspect.getsource(_run_streaming_agent_loop)
        # Should NOT tell agent to "ask up to 5 focused clarifying questions"
        assert "ask up to 5" not in source.lower(), \
            "Forced-final-answer must not tell agent to ask clarifying questions"

    def test_final_directive_encourages_completion(self) -> None:
        from app.agents_system.langgraph.nodes.agent_native import (
            _run_streaming_agent_loop,
        )
        import inspect
        source = inspect.getsource(_run_streaming_agent_loop).lower()
        assert "complete" in source or "best possible" in source or "synthesize" in source


# ---------------------------------------------------------------------------
# Guardrails: allow decisive recommendations
# ---------------------------------------------------------------------------

class TestGuardrailsPrompt:
    """Verify guardrails don't force pure deferral."""

    def _load_prompt(self) -> str:
        path = Path(__file__).parent.parent / "config" / "prompts" / "guardrails.yaml"
        return yaml.safe_load(path.read_text(encoding="utf-8"))["system_prompt"]

    def test_allows_recommendations(self) -> None:
        prompt = self._load_prompt().lower()
        # Should not just say "present options and request a choice"
        # Should say something like "recommend a preferred option"
        assert "recommend" in prompt or "preferred" in prompt


# ---------------------------------------------------------------------------
# Base persona: completeness mandate
# ---------------------------------------------------------------------------

class TestBasePersonaPrompt:
    """Verify base persona includes thoroughness/completeness guidance."""

    def _load_prompt(self) -> str:
        path = Path(__file__).parent.parent / "config" / "prompts" / "base_persona.yaml"
        return yaml.safe_load(path.read_text(encoding="utf-8"))["system_prompt"]

    def test_completeness_directive(self) -> None:
        prompt = self._load_prompt().lower()
        assert "thorough" in prompt or "complete" in prompt or "comprehensive" in prompt


# ---------------------------------------------------------------------------
# Tool strategy: allow broad searches when completeness needed
# ---------------------------------------------------------------------------

class TestToolStrategyPrompt:
    """Verify tool strategy allows comprehensive searches."""

    def _load_prompt(self) -> str:
        path = Path(__file__).parent.parent / "config" / "prompts" / "tool_strategy.yaml"
        return yaml.safe_load(path.read_text(encoding="utf-8"))["system_prompt"]

    def test_no_anti_broad_search(self) -> None:
        prompt = self._load_prompt().lower()
        # Should not discourage broad searches — should encourage thoroughness
        assert "broad, repetitive" not in prompt
