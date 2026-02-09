import pytest

from app.agents_system.config.prompt_loader import PromptLoader
from app.agents_system.langchain.prompt_builder import build_prompt_template


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


def test_cost_estimator_prompt_renders_without_unexpected_variables():
    loader = PromptLoader()
    prompt_cfg = loader.load_prompt("cost_estimator_prompt.yaml")

    template = build_prompt_template(prompt_cfg["system_prompt"], tools=[])

    assert sorted(template.input_variables) == ["agent_scratchpad", "input"]
