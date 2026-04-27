"""Tests for P6: PendingChangeBriefingService.

TDD: tests written before implementation to verify:
- generate_briefing() for propose_candidate stage
- generate_briefing() for pricing stage
- generate_briefing() for validate stage
- Graceful handling of unknown stage / empty pending changes
- Integration: briefing is injected into agent response after persistence
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.features.agent.application.pending_change_briefing_service import (
    PendingChangeBriefingService,
)
from app.features.projects.contracts import (
    ArtifactDraftContract,
    ArtifactDraftType,
    ChangeSetStatus,
    PendingChangeSetContract,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_change_set(
    *,
    stage: str,
    artifact_drafts: list[dict] | None = None,
    bundle_summary: str = "Test change set",
    proposed_patch: dict | None = None,
) -> PendingChangeSetContract:
    return PendingChangeSetContract.model_validate(
        {
            "id": "cs-test-1",
            "projectId": "proj-1",
            "stage": stage,
            "status": ChangeSetStatus.PENDING.value,
            "createdAt": _now(),
            "sourceMessageId": "msg-1",
            "bundleSummary": bundle_summary,
            "proposedPatch": proposed_patch or {},
            "artifactDrafts": artifact_drafts or [],
        }
    )


# ---------------------------------------------------------------------------
# propose_candidate stage
# ---------------------------------------------------------------------------


class TestBriefingProposeCandidate:
    def _change_set(self) -> PendingChangeSetContract:
        return _make_change_set(
            stage="propose_candidate",
            bundle_summary="Hub-and-Spoke with AKS",
            artifact_drafts=[
                {
                    "id": "draft-1",
                    "artifactType": ArtifactDraftType.CANDIDATE_ARCHITECTURE.value,
                    "artifactId": "cand-1",
                    "content": {
                        "title": "Hub-and-Spoke with AKS",
                        "summary": "A hub-and-spoke topology using Azure Kubernetes Service for workloads",
                        "components": [
                            {"name": "Azure Kubernetes Service", "role": "Container orchestration"},
                            {"name": "Azure API Management", "role": "API gateway"},
                            {"name": "Azure Key Vault", "role": "Secret management"},
                        ],
                        "tradeoffs": [
                            "Higher operational complexity for AKS vs PaaS alternatives",
                            "Cost overhead of hub VNet NVA",
                        ],
                        "wafMapping": {
                            "Reliability": "multi-zone AKS node pools",
                            "Security": "private cluster + Key Vault integration",
                            "Cost Optimization": "spot node pools for batch workloads",
                        },
                        "risks": [
                            {
                                "risk": "AKS upgrade friction",
                                "mitigation": "Use node pool maintenance windows and Blue/Green deployments",
                            },
                            {
                                "risk": "Hub NVA single-point-of-failure",
                                "mitigation": "Deploy NVA in active-active HA configuration",
                            },
                        ],
                    },
                    "citations": [],
                    "createdAt": _now(),
                }
            ],
        )

    def test_briefing_contains_candidate_title(self) -> None:
        svc = PendingChangeBriefingService()
        briefing = svc.generate_briefing(self._change_set())
        assert "Hub-and-Spoke with AKS" in briefing

    def test_briefing_contains_components(self) -> None:
        svc = PendingChangeBriefingService()
        briefing = svc.generate_briefing(self._change_set())
        assert "Azure Kubernetes Service" in briefing
        assert "Azure API Management" in briefing

    def test_briefing_contains_tradeoffs(self) -> None:
        svc = PendingChangeBriefingService()
        briefing = svc.generate_briefing(self._change_set())
        assert "operational complexity" in briefing.lower() or "Trade-offs" in briefing

    def test_briefing_contains_waf_mapping(self) -> None:
        svc = PendingChangeBriefingService()
        briefing = svc.generate_briefing(self._change_set())
        assert "Reliability" in briefing or "WAF" in briefing

    def test_briefing_contains_risks(self) -> None:
        svc = PendingChangeBriefingService()
        briefing = svc.generate_briefing(self._change_set())
        assert "AKS upgrade friction" in briefing or "Risks" in briefing

    def test_briefing_contains_change_set_id(self) -> None:
        svc = PendingChangeBriefingService()
        briefing = svc.generate_briefing(self._change_set())
        assert "cs-test-1" in briefing

    def test_briefing_contains_review_instruction(self) -> None:
        svc = PendingChangeBriefingService()
        briefing = svc.generate_briefing(self._change_set())
        assert "Review" in briefing or "review" in briefing

    def test_briefing_without_artifact_drafts_still_works(self) -> None:
        cs = _make_change_set(stage="propose_candidate", bundle_summary="Fallback briefing")
        svc = PendingChangeBriefingService()
        briefing = svc.generate_briefing(cs)
        assert "Fallback briefing" in briefing or "Architect Briefing" in briefing


# ---------------------------------------------------------------------------
# pricing stage
# ---------------------------------------------------------------------------


class TestBriefingPricing:
    def _change_set(self) -> PendingChangeSetContract:
        return _make_change_set(
            stage="pricing",
            bundle_summary="Monthly cost estimate",
            artifact_drafts=[
                {
                    "id": "draft-cost-1",
                    "artifactType": ArtifactDraftType.COST_ESTIMATE.value,
                    "artifactId": "cost-1",
                    "content": {
                        "title": "Monthly cost estimate",
                        "totalMonthlyCost": 4200,
                        "currency": "USD",
                        "confidence": "medium",
                        "costDrivers": [
                            {"name": "AKS node pool (3x Standard_D4s_v3)", "monthlyCost": 1800},
                            {"name": "Azure API Management (Developer tier)", "monthlyCost": 210},
                            {"name": "Azure Firewall (Standard)", "monthlyCost": 730},
                        ],
                        "pricingAssumptions": [
                            "West Europe region",
                            "Pay-as-you-go pricing",
                            "No reserved instances",
                        ],
                        "optimizationOpportunities": [
                            "Switch to Reserved Instances for 30-50% savings",
                        ],
                    },
                    "citations": [],
                    "createdAt": _now(),
                }
            ],
        )

    def test_briefing_contains_total_cost(self) -> None:
        svc = PendingChangeBriefingService()
        briefing = svc.generate_briefing(self._change_set())
        assert "4200" in briefing

    def test_briefing_contains_currency(self) -> None:
        svc = PendingChangeBriefingService()
        briefing = svc.generate_briefing(self._change_set())
        assert "USD" in briefing

    def test_briefing_contains_confidence(self) -> None:
        svc = PendingChangeBriefingService()
        briefing = svc.generate_briefing(self._change_set())
        assert "medium" in briefing.lower()

    def test_briefing_contains_cost_drivers(self) -> None:
        svc = PendingChangeBriefingService()
        briefing = svc.generate_briefing(self._change_set())
        assert "AKS" in briefing or "Cost Drivers" in briefing

    def test_briefing_contains_assumptions(self) -> None:
        svc = PendingChangeBriefingService()
        briefing = svc.generate_briefing(self._change_set())
        assert "West Europe" in briefing or "Assumption" in briefing

    def test_briefing_contains_optimization(self) -> None:
        svc = PendingChangeBriefingService()
        briefing = svc.generate_briefing(self._change_set())
        assert "Reserved" in briefing or "Optimization" in briefing

    def test_briefing_contains_change_set_id(self) -> None:
        svc = PendingChangeBriefingService()
        briefing = svc.generate_briefing(self._change_set())
        assert "cs-test-1" in briefing


# ---------------------------------------------------------------------------
# validate stage
# ---------------------------------------------------------------------------


class TestBriefingValidate:
    def _change_set(self) -> PendingChangeSetContract:
        return _make_change_set(
            stage="validate",
            bundle_summary="WAF validation findings",
            artifact_drafts=[
                {
                    "id": "draft-f1",
                    "artifactType": ArtifactDraftType.FINDING.value,
                    "artifactId": "finding-1",
                    "content": {
                        "title": "No WAF policy attached to API Management",
                        "severity": "high",
                        "description": "APIM instance has no WAF/Azure Front Door policy",
                        "remediation": "Attach Azure Front Door with WAF policy in Prevention mode",
                    },
                    "citations": [],
                    "createdAt": _now(),
                },
                {
                    "id": "draft-f2",
                    "artifactType": ArtifactDraftType.FINDING.value,
                    "artifactId": "finding-2",
                    "content": {
                        "title": "Secrets stored in app config, not Key Vault",
                        "severity": "critical",
                        "description": "Connection strings visible in app configuration",
                        "remediation": "Migrate all secrets to Azure Key Vault and use managed identity",
                    },
                    "citations": [],
                    "createdAt": _now(),
                },
                {
                    "id": "draft-f3",
                    "artifactType": ArtifactDraftType.FINDING.value,
                    "artifactId": "finding-3",
                    "content": {
                        "title": "AKS diagnostics logs not forwarded",
                        "severity": "medium",
                        "description": "No diagnostic settings forwarding AKS logs to Log Analytics",
                        "remediation": "Enable AKS diagnostic settings and configure Log Analytics workspace",
                    },
                    "citations": [],
                    "createdAt": _now(),
                },
            ],
        )

    def test_briefing_contains_total_findings_count(self) -> None:
        svc = PendingChangeBriefingService()
        briefing = svc.generate_briefing(self._change_set())
        assert "3" in briefing

    def test_briefing_contains_severity_breakdown(self) -> None:
        svc = PendingChangeBriefingService()
        briefing = svc.generate_briefing(self._change_set())
        assert "critical" in briefing.lower() or "Severity" in briefing

    def test_briefing_contains_top_findings(self) -> None:
        svc = PendingChangeBriefingService()
        briefing = svc.generate_briefing(self._change_set())
        assert "WAF policy" in briefing or "Secrets" in briefing or "Finding" in briefing

    def test_briefing_contains_remediation(self) -> None:
        svc = PendingChangeBriefingService()
        briefing = svc.generate_briefing(self._change_set())
        assert "Key Vault" in briefing or "remediation" in briefing.lower()

    def test_briefing_contains_change_set_id(self) -> None:
        svc = PendingChangeBriefingService()
        briefing = svc.generate_briefing(self._change_set())
        assert "cs-test-1" in briefing

    def test_briefing_empty_findings_handles_gracefully(self) -> None:
        cs = _make_change_set(stage="validate", bundle_summary="Empty validation")
        svc = PendingChangeBriefingService()
        briefing = svc.generate_briefing(cs)
        assert "0" in briefing or "No validation findings" in briefing


# ---------------------------------------------------------------------------
# Unknown / empty stage handling
# ---------------------------------------------------------------------------


class TestBriefingUnknownStage:
    def test_unknown_stage_returns_generic_briefing(self) -> None:
        cs = _make_change_set(stage="unknown_stage", bundle_summary="Mystery bundle")
        svc = PendingChangeBriefingService()
        briefing = svc.generate_briefing(cs)
        assert "Architect Briefing" in briefing or "Mystery bundle" in briefing
        assert "cs-test-1" in briefing

    def test_empty_stage_returns_generic_briefing(self) -> None:
        cs = _make_change_set(stage="", bundle_summary="Empty stage")
        svc = PendingChangeBriefingService()
        briefing = svc.generate_briefing(cs)
        assert isinstance(briefing, str)
        assert len(briefing) > 0

    def test_empty_change_set_no_drafts_still_returns_string(self) -> None:
        cs = _make_change_set(stage="propose_candidate", bundle_summary="")
        svc = PendingChangeBriefingService()
        briefing = svc.generate_briefing(cs)
        assert isinstance(briefing, str)
        assert "cs-test-1" in briefing


# ---------------------------------------------------------------------------
# clarify stage
# ---------------------------------------------------------------------------


class TestBriefingClarify:
    def _change_set(self) -> PendingChangeSetContract:
        return _make_change_set(
            stage="clarify",
            bundle_summary="Clarification questions",
            artifact_drafts=[
                {
                    "id": "draft-q1",
                    "artifactType": ArtifactDraftType.CLARIFICATION_QUESTION.value,
                    "artifactId": "q-1",
                    "content": {
                        "text": "What is the expected number of concurrent users?",
                        "affectedDecision": "AKS node pool sizing and autoscale configuration",
                        "defaultAssumption": "Assume 500 concurrent users at peak",
                    },
                    "citations": [],
                    "createdAt": _now(),
                }
            ],
        )

    def test_briefing_contains_question(self) -> None:
        svc = PendingChangeBriefingService()
        briefing = svc.generate_briefing(self._change_set())
        assert "concurrent users" in briefing

    def test_briefing_contains_default_assumption(self) -> None:
        svc = PendingChangeBriefingService()
        briefing = svc.generate_briefing(self._change_set())
        assert "500 concurrent users" in briefing or "Default" in briefing

    def test_briefing_contains_affected_decision(self) -> None:
        svc = PendingChangeBriefingService()
        briefing = svc.generate_briefing(self._change_set())
        assert "node pool" in briefing.lower() or "Decision" in briefing


# ---------------------------------------------------------------------------
# Integration: briefing injected into final_answer in postprocess flow
# ---------------------------------------------------------------------------


class TestBriefingIntegrationWithPostprocess:
    """Verify that postprocess_node injects the briefing when pending_change_set exists."""

    def test_postprocess_attaches_generated_briefing_field(self) -> None:
        """postprocess_node must return a 'generated_briefing' key when a pending change set is present."""
        import asyncio

        from app.agents_system.langgraph.nodes.postprocess import postprocess_node
        from app.agents_system.tools.tool_registry import PendingChangeToolResult
        from unittest.mock import MagicMock

        cs = _make_change_set(
            stage="propose_candidate",
            bundle_summary="Integration test candidate",
            artifact_drafts=[
                {
                    "id": "draft-int-1",
                    "artifactType": ArtifactDraftType.CANDIDATE_ARCHITECTURE.value,
                    "artifactId": "cand-int-1",
                    "content": {
                        "title": "Integration Candidate",
                        "summary": "A candidate for integration test",
                        "components": [],
                        "tradeoffs": [],
                        "wafMapping": {},
                        "risks": [],
                    },
                    "citations": [],
                    "createdAt": _now(),
                }
            ],
        )

        tool_result = PendingChangeToolResult(
            type="pending_change_confirmation",
            tool_name="aaa_generate_candidate_architecture",
            stage="propose_candidate",
            message="Candidate saved",
            pending_change_set=cs,
        )

        action_mock = MagicMock()
        action_mock.tool = "aaa_generate_candidate_architecture"
        action_mock.tool_input = {}

        state = {
            "project_id": "proj-1",
            "user_message": "Design an architecture for my app",
            "agent_output": "I've saved your candidate.",
            "intermediate_steps": [(action_mock, tool_result)],
            "current_project_state": {},
        }

        result = asyncio.get_event_loop().run_until_complete(
            postprocess_node(state, response_message_id="msg-test-1")
        )

        assert "generated_briefing" in result
        briefing = result["generated_briefing"]
        assert isinstance(briefing, str)
        assert len(briefing) > 0
        assert "Integration Candidate" in briefing or "Architect Briefing" in briefing

    def test_postprocess_no_briefing_when_no_pending_change_set(self) -> None:
        """When there is no pending change set, generated_briefing should be None or absent."""
        import asyncio

        from app.agents_system.langgraph.nodes.postprocess import postprocess_node

        state = {
            "project_id": "proj-1",
            "user_message": "Tell me about Azure",
            "agent_output": "Azure is a cloud platform.",
            "intermediate_steps": [],
            "current_project_state": {},
        }

        result = asyncio.get_event_loop().run_until_complete(
            postprocess_node(state, response_message_id="msg-test-2")
        )

        # Either absent or None is acceptable
        assert result.get("generated_briefing") is None

    def test_persist_final_answer_uses_briefing_when_output_is_receipt(self) -> None:
        """apply_state_updates_node should prefer the generated_briefing over a thin LLM receipt."""
        import asyncio

        from unittest.mock import AsyncMock, MagicMock, patch

        # We test that when state has generated_briefing and agent_output is a thin receipt,
        # final_answer includes the briefing content.
        thin_receipt = "I've saved your candidate."
        briefing = "## Architect Briefing — Test\n\nA rich briefing.\n\n**Pending Change Set ID:** `cs-1`"

        # Patch the project-state read/write so we don't need a DB
        with (
            patch(
                "app.agents_system.langgraph.nodes.persist.read_project_state",
                new=AsyncMock(return_value={}),
            ),
            patch(
                "app.agents_system.langgraph.nodes.persist.update_project_state",
                new=AsyncMock(),
            ),
            patch(
                "app.agents_system.langgraph.nodes.persist.get_app_settings",
                return_value=MagicMock(aaa_context_debug_enabled=False),
            ),
        ):
            from app.agents_system.langgraph.nodes.persist import apply_state_updates_node

            state = {
                "project_id": "proj-1",
                "user_message": "Design an architecture",
                "agent_output": thin_receipt,
                "generated_briefing": briefing,
                "combined_updates": {"candidateArchitectures": []},
                "architect_choice_required_section": None,
                "next_stage": "propose_candidate",
                "thread_id": None,
            }

            db_mock = MagicMock()

            result = asyncio.get_event_loop().run_until_complete(
                apply_state_updates_node(state, db=db_mock)
            )

        assert "final_answer" in result
        final_answer = result["final_answer"]
        assert "Architect Briefing" in final_answer or "rich briefing" in final_answer.lower()
