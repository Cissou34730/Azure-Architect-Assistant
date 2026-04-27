from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from typing import Any

import pytest


def _load_architecture_planner_module() -> types.ModuleType:
    package_name = "app.agents_system.langgraph.nodes"
    package_path = Path(__file__).resolve().parents[2] / "app" / "agents_system" / "langgraph" / "nodes"
    package_module = sys.modules.get(package_name)
    if package_module is None:
        package_module = types.ModuleType(package_name)
        package_module.__path__ = [str(package_path)]
        sys.modules[package_name] = package_module

    module_name = f"{package_name}.architecture_planner_under_test"
    existing_module = sys.modules.get(module_name)
    if existing_module is not None:
        return existing_module

    spec = importlib.util.spec_from_file_location(
        module_name,
        package_path / "architecture_planner.py",
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load architecture_planner module for tests")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


architecture_planner_module = _load_architecture_planner_module()
_format_previous_decisions = architecture_planner_module._format_previous_decisions
architecture_planner_node = architecture_planner_module.architecture_planner_node


def test_format_previous_decisions_returns_bulleted_summary() -> None:
    formatted = _format_previous_decisions(
        [
            {
                "title": "Use Front Door",
                "rationale": "Global edge routing improves failover behavior.",
            },
            {
                "title": "Prefer managed identity",
                "rationale": "Avoid secret sprawl.",
            },
        ]
    )

    assert formatted == (
        "1. **Use Front Door**\n"
        "   Rationale: Global edge routing improves failover behavior.\n"
        "2. **Prefer managed identity**\n"
        "   Rationale: Avoid secret sprawl."
    )


class _PromptLoaderStub:
    def load_prompt(self, prompt_name: str) -> dict[str, str]:
        assert prompt_name == "architecture_planner_prompt.yaml"
        return {"system_prompt": "Architecture synthesizer system prompt"}

    def load_prompt_file(self, prompt_name: str) -> dict[str, str]:
        assert prompt_name == "architecture_planner_prompt.yaml"
        return {"system_prompt": "Architecture synthesizer system prompt"}


class _RunnerStub:
    mcp_client = object()
    openai_settings = object()


def _build_architecture_planner_state() -> dict[str, Any]:
    return {
        "project_id": "proj-1",
        "next_stage": "propose_candidate",
        "user_message": "Design the target architecture for the workload.",
        "mindmap_guidance": {
            "focus_topics": ["identity", "operations"],
            "suggested_prompts": [
                "Should we de-risk identity before finalizing the candidate?",
            ],
        },
        "current_project_state": {
            "wafChecklist": {
                "items": [
                    {"evaluations": [{"status": "open"}]},
                    {"evaluations": [{"status": "fixed"}]},
                ]
            }
        },
        "agent_handoff_context": {
            "project_context": "B2B workload with internal and partner users.",
            "requirements": "- Support partner onboarding\n- Provide auditability",
            "nfr_summary": "**Reliability:** 99.95% SLA",
            "constraints": {"budget": "< 50k/month", "regions": ["westeurope"]},
            "previous_decisions": [
                {"title": "Use Entra ID", "rationale": "Reuse enterprise identity"}
            ],
            "research_evidence_packets": [
                {
                    "packet_id": "research-packet-1",
                    "focus": "Azure Architecture Center pattern",
                    "query": "propose candidate: Azure Architecture Center pattern",
                    "recommended_sources": ["Azure Architecture Center"],
                }
            ],
            "research_execution_artifact": {
                "status": "completed",
                "packets_created": 1,
            },
        },
        "intermediate_steps": [],
    }


@pytest.mark.asyncio
async def test_architecture_planner_node_builds_reviewable_synthesizer_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_state: dict[str, Any] = {}

    async def _fake_get_agent_runner() -> _RunnerStub:
        return _RunnerStub()

    async def _fake_run_stage_aware_agent(
        state: dict[str, Any],
        *,
        mcp_client: object,
        openai_settings: object,
    ) -> dict[str, Any]:
        captured_state.update(state)
        assert mcp_client is _RunnerStub.mcp_client
        assert openai_settings is _RunnerStub.openai_settings
        return {
            "agent_output": """
# Target Architecture Proposal

## Executive Recommendation
Use Azure Container Apps with Front Door for this B2B workload.

## Workload Classification
- Compute type: containerized
- Data tier: relational
- Integration pattern: sync API
- Deployment model: PaaS

## Evidence Packet Consumption
- research-packet-1 informed the service selection.

## Assumptions linked to requirements
- Assume Microsoft Entra ID remains the enterprise identity provider.

## Trade-offs
- Azure Front Door adds cost but improves resiliency.

## Alternatives Rejected
1. AKS: Rejected because Container Apps provides managed orchestration at lower operational cost.
2. App Service: Rejected because Container Apps supports microservices patterns better.

## Risks and Mitigations
1. Regional outage -> Mitigation: deploy to paired regions.
2. Cost overrun -> Mitigation: set budget alerts.
3. Identity failure -> Mitigation: use Conditional Access policies.

## System Context Diagram [Target Architecture]
```mermaid
graph TD
  User-->Platform
```

### NFR Analysis
**Scalability:** auto-scaling via KEDA

## Container Diagram [Target Architecture]
```mermaid
graph TD
  FrontDoor-->ContainerApps
```

## NFR Achievement Summary
All NFRs are met or addressed.

## WAF Pillar Mapping
| Pillar | Status | How addressed |
|--------|--------|--------------|
| Reliability | addressed | Front Door + zone redundancy |

## NFR Achievement Matrix
| NFR | Status | Notes |
|-----|--------|-------|
| 99.95% SLA | achieved | Front Door + HA |

## Cost Drivers
- Front Door: egress cost -> optimization lever: Reserved pricing

## Operational Model
- Deployment pipeline: Azure DevOps with blue-green deployments

## Security Model
- Identity: Entra ID with RBAC and Conditional Access

## ADR Candidates
- [ ] Hosting model: Container Apps vs AKS – key decision point

## Implementation Phases

### Phase 1: Foundation
Core Container Apps, Front Door, Entra ID.

### Phase 2: Full Target
Full HA, monitoring, all integrations.

## WAF Delta
- Reliability: add Front Door and zone redundancy.

## Mindmap Delta
- Identity and operations coverage improved.

## Citations
- Azure Architecture Center | https://learn.microsoft.com/example

AAA_STATE_UPDATE
```json
{"candidateArchitectures":[{"id":"cand-1","title":"Primary candidate","summary":"Front Door plus Container Apps"}]}
```
""".strip(),
            "intermediate_steps": [("tool", "used aaa_generate_candidate_architecture")],
            "success": True,
            "error": None,
        }

    monkeypatch.setattr(architecture_planner_module, "PromptLoader", _PromptLoaderStub)
    monkeypatch.setattr(
        architecture_planner_module,
        "get_agent_runner",
        _fake_get_agent_runner,
    )
    monkeypatch.setattr(
        architecture_planner_module,
        "run_stage_aware_agent",
        _fake_run_stage_aware_agent,
    )

    result = await architecture_planner_node(_build_architecture_planner_state())

    planner_input = str(captured_state["user_message"])
    assert "Default to exactly 1 candidate unless the user explicitly asks for more." in planner_input
    assert "**WAF Snapshot:**" in planner_input
    assert "**Mind Map Delta Targets:**" in planner_input
    assert "**Research Execution Artifact:**" in planner_input
    assert "Evidence Packet Consumption" in planner_input

    execution_artifact = result["architecture_synthesis_execution_artifact"]
    assert execution_artifact["status"] == "completed"
    assert execution_artifact["stage"] == "propose_candidate"
    assert execution_artifact["review_mode"] == "postprocess_pending_changes"
    assert execution_artifact["research_packets_supplied"] == 1
    assert execution_artifact["required_sections"] == {
        "assumptions": True,
        "trade_offs": True,
        "citations": True,
        "waf_delta": True,
        "mindmap_delta": True,
        "c4_system_context": True,
        "c4_container": True,
        "state_update": True,
        # P3 + P11 new sections – all present in the updated mock output
        "executive_recommendation": True,
        "workload_classification": True,
        "alternatives_rejected": True,
        "risks_and_mitigations": True,
        "waf_pillar_mapping": True,
        "nfr_achievement_matrix": True,
        "cost_drivers": True,
        "operational_model": True,
        "security_model": True,
        "adr_candidates": True,
        "implementation_phases": True,
    }
    assert execution_artifact["missing_sections"] == []


@pytest.mark.asyncio
async def test_architecture_planner_node_records_failed_execution_artifact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake_get_agent_runner() -> _RunnerStub:
        return _RunnerStub()

    async def _failing_run_stage_aware_agent(
        state: dict[str, Any],
        *,
        mcp_client: object,
        openai_settings: object,
    ) -> dict[str, Any]:
        raise RuntimeError("planner offline")

    monkeypatch.setattr(architecture_planner_module, "PromptLoader", _PromptLoaderStub)
    monkeypatch.setattr(
        architecture_planner_module,
        "get_agent_runner",
        _fake_get_agent_runner,
    )
    monkeypatch.setattr(
        architecture_planner_module,
        "run_stage_aware_agent",
        _failing_run_stage_aware_agent,
    )

    result = await architecture_planner_node(_build_architecture_planner_state())

    assert result["success"] is False
    assert result["current_agent"] == "main"
    assert result["architecture_synthesis_execution_artifact"] == {
        "status": "failed",
        "stage": "propose_candidate",
        "prompt": "architecture_planner_prompt.yaml",
        "reason": "runtime_error",
        "review_mode": "postprocess_pending_changes",
    }


# ---------------------------------------------------------------------------
# P3 + P11: Prompt content and execution-artifact section-detection tests
# ---------------------------------------------------------------------------

_PROMPT_PATH = (
    Path(__file__).resolve().parents[2] / "config" / "prompts" / "architecture_planner_prompt.yaml"
)


def test_architecture_planner_prompt_has_required_consulting_sections() -> None:
    """P3: architecture_planner_prompt.yaml must contain all required consulting-quality sections."""
    content = _PROMPT_PATH.read_text(encoding="utf-8").lower()
    required = [
        "executive recommendation",
        "workload classification",
        "alternatives rejected",
        "risks and mitigations",
        "waf pillar mapping",
        "nfr achievement",
        "cost drivers",
        "operational model",
        "security model",
        "adr candidates",
        "implementation phases",
    ]
    for section in required:
        assert section in content, f"Missing required section in prompt: '{section}'"


def test_architecture_planner_prompt_has_adr_candidate_detection_domains() -> None:
    """P11: Prompt must require detection of the seven major architectural decision domains."""
    content = _PROMPT_PATH.read_text(encoding="utf-8").lower()
    required_domains = [
        "hosting model",
        "database choice",
        "identity model",
        "network exposure",
        "regional",
        "integration pattern",
        "observability",
    ]
    for domain in required_domains:
        assert domain in content, f"Missing ADR candidate detection domain: '{domain}'"


def test_architecture_planner_prompt_output_format_includes_adr_candidates_field() -> None:
    """P11: The output format must explicitly list adrCandidates."""
    content = _PROMPT_PATH.read_text(encoding="utf-8")
    assert "adrCandidates" in content, "Output format must include adrCandidates field"


def test_build_synthesizer_contract_requires_new_consulting_sections() -> None:
    """P3: _build_synthesizer_contract must mandate all consulting-quality sections."""
    _build_synthesizer_contract = architecture_planner_module._build_synthesizer_contract
    state = _build_architecture_planner_state()
    handoff_context = state["agent_handoff_context"]
    contract = _build_synthesizer_contract(state, handoff_context).lower()

    required = [
        "executive recommendation",
        "alternatives rejected",
        "risks and mitigations",
        "waf pillar mapping",
        "adr candidates",
        "implementation phases",
        "cost drivers",
        "security model",
        "operational model",
    ]
    for section in required:
        assert section in contract, f"Synthesizer contract missing directive for: '{section}'"


def test_build_synthesis_execution_artifact_new_section_keys_present() -> None:
    """P3: required_sections must include all P3+P11 keys."""
    _build_synthesis_execution_artifact = architecture_planner_module._build_synthesis_execution_artifact
    state = _build_architecture_planner_state()

    artifact = _build_synthesis_execution_artifact(
        state=state,
        agent_output="",
        success=True,
        error=None,
        research_packets_supplied=0,
    )

    new_keys = [
        "executive_recommendation",
        "workload_classification",
        "alternatives_rejected",
        "risks_and_mitigations",
        "waf_pillar_mapping",
        "nfr_achievement_matrix",
        "cost_drivers",
        "operational_model",
        "security_model",
        "adr_candidates",
        "implementation_phases",
    ]
    for key in new_keys:
        assert key in artifact["required_sections"], f"required_sections missing key: '{key}'"


def test_build_synthesis_execution_artifact_exposes_missing_sections() -> None:
    """P3: missing_sections must list sections absent from sparse output."""
    _build_synthesis_execution_artifact = architecture_planner_module._build_synthesis_execution_artifact
    state = _build_architecture_planner_state()

    sparse_output = "## Trade-offs\nSome tradeoff\n\n## Citations\nSome citation\n\n## WAF Delta\nSome WAF finding"

    artifact = _build_synthesis_execution_artifact(
        state=state,
        agent_output=sparse_output,
        success=True,
        error=None,
        research_packets_supplied=0,
    )

    assert "missing_sections" in artifact, "Execution artifact must have missing_sections field"
    missing = artifact["missing_sections"]
    assert isinstance(missing, list)
    # Absent sections must be flagged
    assert "adr_candidates" in missing
    assert "alternatives_rejected" in missing
    assert "risks_and_mitigations" in missing
    assert "executive_recommendation" in missing
    # Present sections must NOT appear in missing
    assert "trade_offs" not in missing
    assert "citations" not in missing
    assert "waf_delta" not in missing
