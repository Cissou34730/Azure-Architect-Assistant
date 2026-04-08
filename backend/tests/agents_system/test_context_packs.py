"""Tests for context pack service and stage packers."""

from __future__ import annotations

import pytest

from app.agents_system.memory.context_packs.schema import ContextPack, ContextSection
from app.agents_system.memory.context_packs.service import build_context_pack
from app.agents_system.memory.context_packs.stage_packers import (
    build_clarify_sections,
    build_iac_sections,
    build_manage_adr_sections,
    build_pricing_sections,
    build_propose_candidate_sections,
    build_validate_sections,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def rich_state() -> dict:
    """A state dict with realistic project data for all stages."""
    return {
        "context": {
            "summary": "Cloud migration for retail platform",
            "objectives": ["High availability", "Cost optimization"],
            "scenarioType": "migration",
        },
        "nfrs": {
            "availability": "99.95%",
            "security": "SOC2 compliant",
            "performance": "< 200ms P95",
            "costConstraints": "Max $10K/month",
        },
        "technicalConstraints": {
            "constraints": ["Azure only", "No public IPs"],
            "assumptions": ["Team knows Terraform"],
        },
        "requirements": [
            {"category": "functional", "text": "User login via AAD"},
            {"category": "non-functional", "text": "Auto-scaling enabled"},
        ],
        "openQuestions": ["Which region for DR?", "Shared or dedicated DB?"],
        "clarificationQuestions": [
            {"question": "What RTO/RPO targets?", "priority": 1},
            {"question": "Any existing landing zone?", "priority": 2},
        ],
        "architectureDecisions": [
            {"title": "Use AKS over App Service", "status": "accepted"},
            {"title": "Event-driven with Event Grid", "status": "proposed"},
        ],
        "dataCompliance": {
            "dataTypes": ["PII", "Financial"],
            "complianceRequirements": ["GDPR", "PCI-DSS"],
            "dataResidency": "EU West",
        },
        "wafChecklist": {
            "items": [
                {"title": "Enable RBAC", "pillar": "security", "status": "done"},
                {"title": "Configure WAF", "pillar": "security", "status": "pending"},
                {"title": "Set up DR", "pillar": "reliability", "status": "pending"},
            ],
        },
    }


@pytest.fixture()
def minimal_state() -> dict:
    """Bare minimum state with just context summary."""
    return {
        "context": {"summary": "A small project"},
    }


# ── Stage packer tests ──────────────────────────────────────────────────────

class TestStagePacker:
    """Verify each stage packer returns non-empty sections from rich state."""

    def test_clarify_sections_include_questions(self, rich_state: dict) -> None:
        sections = build_clarify_sections(rich_state)
        names = [s.name for s in sections]
        assert "project_facts" in names
        assert "clarification_questions" in names

    def test_propose_candidate_sections_include_requirements(self, rich_state: dict) -> None:
        sections = build_propose_candidate_sections(rich_state)
        names = [s.name for s in sections]
        assert "requirements" in names
        assert "constraints" in names

    def test_manage_adr_sections_include_decisions(self, rich_state: dict) -> None:
        sections = build_manage_adr_sections(rich_state)
        names = [s.name for s in sections]
        assert "decisions" in names

    def test_manage_adr_sections_support_canonical_adrs(self) -> None:
        sections = build_manage_adr_sections(
            {
                "context": {"summary": "ADR flow"},
                "adrs": [
                    {"title": "Use AKS over App Service", "status": "accepted"},
                    {"title": "Split workloads by bounded context", "status": "proposed"},
                ],
            }
        )

        decisions = next(section for section in sections if section.name == "decisions")
        assert "[accepted] Use AKS over App Service" in decisions.content
        assert "[proposed] Split workloads by bounded context" in decisions.content

    def test_validate_sections_include_waf(self, rich_state: dict) -> None:
        sections = build_validate_sections(rich_state)
        names = [s.name for s in sections]
        assert "waf_checklist" in names

    def test_validate_sections_support_canonical_waf_evaluations(self) -> None:
        sections = build_validate_sections(
            {
                "context": {"summary": "Validation flow"},
                "wafChecklist": {
                    "items": [
                        {
                            "pillar": "Security",
                            "topic": "Enable RBAC",
                            "evaluations": [{"status": "fixed"}],
                        },
                        {
                            "pillar": "Reliability",
                            "topic": "Set up DR",
                            "evaluations": [{"status": "open"}],
                        },
                    ]
                },
            }
        )

        waf = next(section for section in sections if section.name == "waf_checklist")
        assert "WAF CHECKLIST: 1/2 items completed" in waf.content
        assert "[ ] Set up DR (Reliability)" in waf.content

    def test_validate_sections_support_waf_items_dict_shape(self) -> None:
        sections = build_validate_sections(
            {
                "context": {"summary": "Validation flow"},
                "wafChecklist": {
                    "items": {
                        "sec-01": {
                            "pillar": "Security",
                            "topic": "Managed identities",
                            "evaluations": [{"status": "in_progress"}],
                        }
                    }
                },
            }
        )

        waf = next(section for section in sections if section.name == "waf_checklist")
        assert "WAF CHECKLIST: 0/1 items completed" in waf.content
        assert "[ ] Managed identities (Security)" in waf.content

    def test_pricing_sections_include_pricing(self, rich_state: dict) -> None:
        sections = build_pricing_sections(rich_state)
        names = [s.name for s in sections]
        assert "pricing_assumptions" in names

    def test_iac_sections_include_constraints_and_decisions(self, rich_state: dict) -> None:
        sections = build_iac_sections(rich_state)
        names = [s.name for s in sections]
        assert "constraints" in names
        assert "decisions" in names

    def test_empty_state_returns_project_facts_only(self) -> None:
        sections = build_clarify_sections({})
        assert len(sections) == 0  # no content → all filtered

    def test_minimal_state_returns_facts(self, minimal_state: dict) -> None:
        sections = build_clarify_sections(minimal_state)
        names = [s.name for s in sections]
        assert "project_facts" in names

    def test_thread_summary_injected(self, rich_state: dict) -> None:
        sections = build_clarify_sections(rich_state, thread_summary="Prior context here")
        names = [s.name for s in sections]
        assert "thread_summary" in names
        summary_section = next(s for s in sections if s.name == "thread_summary")
        assert "Prior context here" in summary_section.content

    def test_thread_summary_excluded_when_none(self, rich_state: dict) -> None:
        sections = build_clarify_sections(rich_state, thread_summary=None)
        names = [s.name for s in sections]
        assert "thread_summary" not in names


# ── Service tests ────────────────────────────────────────────────────────────

class TestContextPackService:
    """Tests for the build_context_pack service function."""

    def test_returns_context_pack(self, rich_state: dict) -> None:
        pack = build_context_pack("clarify", rich_state)
        assert isinstance(pack, ContextPack)
        assert pack.stage == "clarify"
        assert len(pack.sections) > 0

    def test_budget_meta_present(self, rich_state: dict) -> None:
        pack = build_context_pack("clarify", rich_state, budget_tokens=4000)
        assert "budget_tokens" in pack.budget_meta
        assert "used_tokens" in pack.budget_meta
        assert "dropped_sections" in pack.budget_meta

    def test_sections_have_token_counts(self, rich_state: dict) -> None:
        pack = build_context_pack("clarify", rich_state)
        for section in pack.sections:
            assert section.token_count >= 0

    def test_budget_respected(self, rich_state: dict) -> None:
        pack = build_context_pack("clarify", rich_state, budget_tokens=10)
        assert pack.budget_meta["used_tokens"] <= 10

    def test_low_budget_drops_sections(self, rich_state: dict) -> None:
        pack = build_context_pack("clarify", rich_state, budget_tokens=10)
        assert len(pack.budget_meta["dropped_sections"]) > 0

    def test_unknown_stage_falls_back(self, rich_state: dict) -> None:
        pack = build_context_pack("unknown_stage", rich_state)
        assert isinstance(pack, ContextPack)
        assert pack.stage == "unknown_stage"
        # Falls back to clarify packer, should still produce sections
        assert len(pack.sections) > 0

    def test_to_prompt_produces_text(self, rich_state: dict) -> None:
        pack = build_context_pack("propose_candidate", rich_state)
        prompt = pack.to_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_all_registered_stages(self, rich_state: dict) -> None:
        for stage in ("clarify", "propose_candidate", "manage_adr", "validate", "pricing", "iac"):
            pack = build_context_pack(stage, rich_state)
            assert pack.stage == stage
            assert len(pack.sections) > 0


# ── Schema tests ─────────────────────────────────────────────────────────────

class TestContextSection:
    def test_section_defaults(self) -> None:
        s = ContextSection(name="test", content="hello")
        assert s.token_count == 0
        assert s.priority == 1

    def test_context_pack_total_tokens(self) -> None:
        pack = ContextPack(
            stage="test",
            sections=[
                ContextSection(name="a", content="x", token_count=10),
                ContextSection(name="b", content="y", token_count=20),
            ],
        )
        assert pack.total_tokens == 30

    def test_context_pack_to_prompt(self) -> None:
        pack = ContextPack(
            stage="test",
            sections=[
                ContextSection(name="a", content="Alpha"),
                ContextSection(name="b", content="Beta"),
            ],
        )
        prompt = pack.to_prompt()
        assert "Alpha" in prompt
        assert "Beta" in prompt

    def test_context_pack_section_names(self) -> None:
        pack = ContextPack(
            stage="test",
            sections=[
                ContextSection(name="a", content="x"),
                ContextSection(name="b", content="y"),
            ],
        )
        assert pack.section_names() == ["a", "b"]
