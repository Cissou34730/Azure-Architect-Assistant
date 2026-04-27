from __future__ import annotations

from app.agents_system.config.prompt_loader import PromptLoader, _SHARED_PROMPT_FILES


def test_compose_prompt_skips_orchestrator_routing_for_stage_worker_prompts() -> None:
    loader = PromptLoader()

    prompt = loader.compose_prompt(
        agent_type="orchestrator",
        stage="validate",
        context_budget=8_000,
    )

    assert "**WAF validator**" in prompt
    assert "**Orchestrator routing**" not in prompt


def test_architect_briefing_in_shared_prompt_files() -> None:
    assert "architect_briefing.yaml" in _SHARED_PROMPT_FILES


def test_architect_briefing_yaml_is_parseable_with_expected_stage_keys() -> None:
    loader = PromptLoader()
    data = loader.load_prompt_file("architect_briefing.yaml")
    assert isinstance(data, dict)
    expected = {"propose_candidate", "validate", "pricing", "iac", "clarify"}
    stages = data.get("stages")
    assert isinstance(stages, dict)
    missing = expected - set(stages.keys())
    assert not missing, f"Missing stage keys: {missing}"


def test_orchestrator_prompt_includes_all_shared_layers() -> None:
    loader = PromptLoader()
    prompt = loader.compose_prompt(
        agent_type="orchestrator",
        stage="propose_candidate",
        context_budget=0,
    )
    assert "Constitution" in prompt or "constitution" in prompt.lower()
    assert "proactive" in prompt.lower()
    assert "Tool strategy" in prompt or "tool strategy" in prompt.lower()
    assert "Guardrails" in prompt or "guardrail" in prompt.lower()
    assert "Architect Briefing" in prompt


def test_architect_briefing_system_prompt_contains_stage_instructions() -> None:
    loader = PromptLoader()
    data = loader.load_prompt_file("architect_briefing.yaml")
    sp = data.get("system_prompt", "")
    assert "propose_candidate" in sp or "Recommend" in sp
    assert "validate" in sp or "WAF" in sp


def test_shared_prompt_files_order() -> None:
    files = list(_SHARED_PROMPT_FILES)
    assert "base_persona.yaml" in files
    assert "architect_briefing.yaml" in files
    assert files.index("architect_briefing.yaml") > files.index("base_persona.yaml")