import pytest

from app.agents_system.config.prompt_loader import PromptLoader
from app.agents_system.config.react_prompts import _format_few_shot_examples
from app.agents_system.langgraph.nodes.agent_native import _build_system_directives
from app.agents_system.memory.token_counter import TokenCounter
from app.agents_system.services.adr_drafter_worker import ADRDrafterWorker


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


def test_requirements_extraction_prompt_contains_required_fields():
    loader = PromptLoader()
    prompt_cfg = loader.load_prompt("requirements_extraction.yaml")

    system_prompt = prompt_cfg.get("system_prompt")
    assert isinstance(system_prompt, str)
    assert system_prompt.strip()
    assert "project_document_search" in system_prompt
    assert "aaa_manage_artifacts" in system_prompt


def test_clarification_planner_prompt_covers_ambiguities_and_history():
    loader = PromptLoader()
    prompt_cfg = loader.load_prompt("clarification_planner.yaml")

    system_prompt = str(prompt_cfg.get("system_prompt", "")).lower()
    assert "ambigu" in system_prompt
    assert "3-5" in system_prompt
    assert "prior clarification" in system_prompt or "don't re-ask" in system_prompt


def test_architecture_planner_prompt_requires_evidence_mapping_and_deltas():
    loader = PromptLoader()
    prompt_cfg = loader.load_prompt("architecture_planner_prompt.yaml")

    system_prompt = str(prompt_cfg.get("system_prompt", "")).lower()
    assert "evidence" in system_prompt
    assert "packet" in system_prompt
    assert "requirement" in system_prompt
    assert "waf delta" in system_prompt or "mindmap delta" in system_prompt
    assert "```mermaid" in system_prompt


def test_adr_writer_prompt_mentions_lifecycle_and_traceability():
    loader = PromptLoader()
    prompt_cfg = loader.load_prompt("adr_writer.yaml")

    system_prompt = str(prompt_cfg.get("system_prompt", "")).lower()
    assert "traceability" in system_prompt or "traceable" in system_prompt
    assert "alternatives" in system_prompt
    assert "supersed" in system_prompt
    assert "example adr" in system_prompt or "example:" in system_prompt


def test_waf_validator_prompt_mentions_severity_and_source_urls():
    loader = PromptLoader()
    prompt_cfg = loader.load_prompt("waf_validator.yaml")

    system_prompt = str(prompt_cfg.get("system_prompt", "")).lower()
    assert "critical" in system_prompt
    assert "high" in system_prompt
    assert "medium" in system_prompt
    assert "low" in system_prompt
    assert "url" in system_prompt
    assert "finding id" in system_prompt
    assert "remediation" in system_prompt


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


def test_compose_prompt_combines_shared_and_stage_files(tmp_path):
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "agent_prompts.yaml").write_text(
        "system_prompt: legacy base\nreact_template: base_template\n",
        encoding="utf-8",
    )
    (prompts_dir / "base_persona.yaml").write_text(
        "system_prompt: |\n  Base persona for ${agent_type}\n",
        encoding="utf-8",
    )
    (prompts_dir / "orchestrator_routing.yaml").write_text(
        "system_prompt: |\n  Routing for ${stage}\n",
        encoding="utf-8",
    )
    (prompts_dir / "tool_strategy.yaml").write_text(
        "system_prompt: |\n  Tool strategy\n",
        encoding="utf-8",
    )
    (prompts_dir / "guardrails.yaml").write_text(
        "system_prompt: |\n  Guardrails with ${context_budget} token budget\n",
        encoding="utf-8",
    )
    (prompts_dir / "clarification_planner.yaml").write_text(
        "system_prompt: |\n  Clarify stage prompt\n",
        encoding="utf-8",
    )

    loader = PromptLoader(prompts_dir=prompts_dir)

    prompt = loader.compose_prompt(
        agent_type="orchestrator",
        stage="clarify",
        context_budget=512,
    )

    assert "Base persona for orchestrator" in prompt
    assert "Routing for clarify" in prompt
    assert "Tool strategy" in prompt
    assert "Guardrails with 512 token budget" in prompt
    assert "Clarify stage prompt" in prompt


def test_compose_prompt_falls_back_to_legacy_system_prompt(tmp_path):
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "agent_prompts.yaml").write_text(
        "system_prompt: legacy base prompt\nreact_template: base_template\n",
        encoding="utf-8",
    )

    loader = PromptLoader(prompts_dir=prompts_dir)

    prompt = loader.compose_prompt(
        agent_type="orchestrator",
        stage="clarify",
        context_budget=256,
    )

    assert prompt == "legacy base prompt"


def test_compose_prompt_truncates_to_context_budget(tmp_path):
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    large_prompt = " ".join(["architecture"] * 64)
    (prompts_dir / "agent_prompts.yaml").write_text(
        "system_prompt: legacy base prompt\nreact_template: base_template\n",
        encoding="utf-8",
    )
    (prompts_dir / "base_persona.yaml").write_text(
        f"system_prompt: |\n  {large_prompt}\n",
        encoding="utf-8",
    )

    loader = PromptLoader(prompts_dir=prompts_dir)

    prompt = loader.compose_prompt(
        agent_type="orchestrator",
        stage="clarify",
        context_budget=16,
    )

    assert TokenCounter().count_tokens(prompt) <= 16
    assert prompt != large_prompt


def test_compose_prompt_truncates_legacy_prompt_when_modular_files_are_missing(tmp_path):
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    large_prompt = " ".join(["legacy"] * 64)
    (prompts_dir / "agent_prompts.yaml").write_text(
        f"system_prompt: |\n  {large_prompt}\nreact_template: base_template\n",
        encoding="utf-8",
    )

    loader = PromptLoader(prompts_dir=prompts_dir)

    prompt = loader.compose_prompt(
        agent_type="orchestrator",
        stage="clarify",
        context_budget=12,
    )

    assert TokenCounter().count_tokens(prompt) <= 12
    assert prompt != large_prompt


def test_compose_prompt_does_not_truncate_when_budget_is_not_positive(tmp_path):
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    large_prompt = " ".join(["architecture"] * 64)
    (prompts_dir / "agent_prompts.yaml").write_text(
        "system_prompt: legacy base prompt\nreact_template: base_template\n",
        encoding="utf-8",
    )
    (prompts_dir / "base_persona.yaml").write_text(
        f"system_prompt: |\n  {large_prompt}\n",
        encoding="utf-8",
    )

    loader = PromptLoader(prompts_dir=prompts_dir)

    prompt = loader.compose_prompt(
        agent_type="orchestrator",
        stage="clarify",
        context_budget=0,
    )

    assert prompt == large_prompt
    assert TokenCounter().count_tokens(prompt) > 12


def test_build_system_directives_uses_reloaded_prompt(tmp_path):
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "agent_prompts.yaml").write_text(
        "system_prompt: legacy base\nreact_template: base_template\n",
        encoding="utf-8",
    )
    base_persona = prompts_dir / "base_persona.yaml"
    base_persona.write_text(
        "system_prompt: first prompt\n",
        encoding="utf-8",
    )
    (prompts_dir / "orchestrator_routing.yaml").write_text(
        "system_prompt: routing prompt\n",
        encoding="utf-8",
    )
    (prompts_dir / "tool_strategy.yaml").write_text(
        "system_prompt: tool prompt\n",
        encoding="utf-8",
    )
    (prompts_dir / "guardrails.yaml").write_text(
        "system_prompt: guardrail prompt\n",
        encoding="utf-8",
    )
    (prompts_dir / "clarification_planner.yaml").write_text(
        "system_prompt: clarify prompt\n",
        encoding="utf-8",
    )

    original_instance = PromptLoader.get_instance()
    loader = PromptLoader(prompts_dir=prompts_dir)
    PromptLoader.set_instance(loader)
    try:
        first = _build_system_directives({})
        assert "first prompt" in first

        base_persona.write_text(
            "system_prompt: second prompt\n",
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


def _citation(citation_id: str) -> dict[str, str]:
    return {
        "id": citation_id,
        "kind": "referenceDocument",
        "referenceDocumentId": f"ref-{citation_id}",
    }


class _ADRPromptLoaderStub:
    def __init__(self, system_prompt: str) -> None:
        self.system_prompt = system_prompt
        self.loaded: list[str] = []

    def load_prompt(self, prompt_name: str) -> dict[str, str]:
        self.loaded.append(prompt_name)
        return {"system_prompt": self.system_prompt}


@pytest.mark.asyncio
async def test_adr_drafter_worker_uses_existing_prompt_and_validates_structured_output() -> None:
    prompt_loader = _ADRPromptLoaderStub("Write structured ADRs only.")
    captured: dict[str, str] = {}

    async def _generator(system_prompt: str, user_prompt: str) -> dict[str, object]:
        captured["system_prompt"] = system_prompt
        captured["user_prompt"] = user_prompt
        return {
            "action": "create",
            "adr": {
                "title": "Use Azure SQL Database",
                "context": "The workload needs relational consistency.",
                "decision": "Adopt Azure SQL Database for the transactional store.",
                "consequences": "Improves operability but reduces schema flexibility.",
                "alternativesConsidered": [
                    "Azure Cosmos DB",
                    "Azure Database for PostgreSQL",
                ],
                "relatedRequirementIds": ["req-1"],
                "relatedDiagramIds": ["diag-1"],
                "sourceCitations": [_citation("cite-1")],
            },
        }

    worker = ADRDrafterWorker(generator=_generator, prompt_loader=prompt_loader)

    result = await worker.draft_adr(
        user_message="Create an ADR for the primary data store.",
        project_state={
            "requirements": [{"id": "req-1", "text": "Relational consistency"}],
            "candidateArchitectures": [{"id": "arch-1", "title": "App + SQL"}],
        },
        requested_action="create",
    )

    assert prompt_loader.loaded == ["adr_writer.yaml"]
    assert captured["system_prompt"] == "Write structured ADRs only."
    assert "responseContract" in captured["user_prompt"]
    assert "Create an ADR for the primary data store." in captured["user_prompt"]
    assert result.action == "create"
    assert result.adr.title == "Use Azure SQL Database"
    assert result.adr.alternatives_considered == [
        "Azure Cosmos DB",
        "Azure Database for PostgreSQL",
    ]


@pytest.mark.asyncio
async def test_adr_drafter_worker_rejects_missing_alternatives_considered() -> None:
    async def _generator(system_prompt: str, user_prompt: str) -> dict[str, object]:
        return {
            "action": "create",
            "adr": {
                "title": "Use Azure SQL Database",
                "context": "ctx",
                "decision": "decision",
                "consequences": "cons",
                "relatedRequirementIds": ["req-1"],
                "sourceCitations": [_citation("cite-1")],
                "missingEvidenceReason": "No diagrams exist yet.",
            },
        }

    worker = ADRDrafterWorker(
        generator=_generator,
        prompt_loader=_ADRPromptLoaderStub("Write structured ADRs only."),
    )

    with pytest.raises(ValueError, match="alternativesConsidered"):
        await worker.draft_adr(
            user_message="Create an ADR for the primary data store.",
            project_state={},
            requested_action="create",
        )
