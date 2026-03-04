import pytest

from app.agents_system.config.prompt_loader import PromptLoader
from app.agents_system.config.react_prompts import _format_few_shot_examples
from app.agents_system.langgraph.nodes.agent_native import _build_system_directives


def test_load_prompt_from_specialized_file(tmp_path):
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "agent_prompts.yaml").write_text(
        "system_prompt: base\nreact_template: base_template\n",
        encoding="utf-8",
    )
    (prompts_dir / "architecture_planner_prompt.yaml").write_text(
        "system_prompt: planner\nreact_template: planner_template\n",
        encoding="utf-8",
    )

    loader = PromptLoader(prompts_dir=prompts_dir)

    prompt = loader.load_prompt("architecture_planner_prompt.yaml")

    assert prompt["system_prompt"] == "planner"
    assert prompt["react_template"] == "planner_template"


def test_load_prompt_falls_back_to_section_in_agent_prompts(tmp_path):
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "agent_prompts.yaml").write_text(
        "\n".join(
            [
                "system_prompt: base",
                "react_template: base_template",
                "architecture_planner_prompt:",
                "  system_prompt: planner",
                "  react_template: planner_template",
                "",
            ]
        ),
        encoding="utf-8",
    )

    loader = PromptLoader(prompts_dir=prompts_dir)

    prompt = loader.load_prompt("architecture_planner_prompt.yaml")

    assert prompt["system_prompt"] == "planner"
    assert prompt["react_template"] == "planner_template"


def test_load_prompt_raises_when_missing(tmp_path):
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "agent_prompts.yaml").write_text(
        "system_prompt: base\nreact_template: base_template\n",
        encoding="utf-8",
    )

    loader = PromptLoader(prompts_dir=prompts_dir)

    with pytest.raises(FileNotFoundError) as exc:
        loader.load_prompt("missing_prompt.yaml")
    assert "missing_prompt.yaml" in str(exc.value)


def test_cost_estimator_prompt_contains_required_fields():
    loader = PromptLoader()
    prompt_cfg = loader.load_prompt("cost_estimator_prompt.yaml")

    assert isinstance(prompt_cfg.get("system_prompt"), str)
    assert prompt_cfg["system_prompt"].strip()
    assert isinstance(prompt_cfg.get("version"), str)


def test_load_prompts_returns_defensive_copy(tmp_path):
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "agent_prompts.yaml").write_text(
        "system_prompt: base\nreact_template: base_template\n",
        encoding="utf-8",
    )

    loader = PromptLoader(prompts_dir=prompts_dir)
    prompts_a = loader.load_prompts()
    prompts_a["system_prompt"] = "mutated"
    prompts_b = loader.load_prompts()

    assert prompts_b["system_prompt"] == "base"


def test_build_system_directives_uses_reloaded_prompt(tmp_path):
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    prompts_file = prompts_dir / "agent_prompts.yaml"
    prompts_file.write_text(
        "system_prompt: first prompt\nreact_template: base_template\n",
        encoding="utf-8",
    )

    original_instance = PromptLoader.get_instance()
    loader = PromptLoader(prompts_dir=prompts_dir)
    PromptLoader.set_instance(loader)
    try:
        first = _build_system_directives({})
        assert "first prompt" in first

        prompts_file.write_text(
            "system_prompt: second prompt\nreact_template: base_template\n",
            encoding="utf-8",
        )
        loader.reload()

        second = _build_system_directives({})
        assert "second prompt" in second
    finally:
        PromptLoader.set_instance(original_instance)


def test_format_few_shot_examples_handles_missing_keys():
    formatted = _format_few_shot_examples([{"name": "Only name"}])
    assert "Example 1: Only name" in formatted
    assert "Question:" in formatted


def test_format_few_shot_examples_skips_non_mappings():
    formatted = _format_few_shot_examples([{"name": "valid", "question": "q", "reasoning": "r"}, "bad"])
    assert "Example 1: valid" in formatted
    assert "Example 2:" not in formatted
