from __future__ import annotations

from app.agents_system.config.prompt_loader import PromptLoader


def test_compose_prompt_skips_orchestrator_routing_for_stage_worker_prompts() -> None:
    loader = PromptLoader()

    prompt = loader.compose_prompt(
        agent_type="orchestrator",
        stage="validate",
        context_budget=8_000,
    )

    assert "**WAF validator**" in prompt
    assert "**Orchestrator routing**" not in prompt
