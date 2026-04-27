"""Tests for P4+P7: Expanded candidate architecture schema and research traceability.

TDD: These tests were written BEFORE the implementation.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import pytest

from app.features.agent.infrastructure.tools.aaa_candidate_tool import (
    AAAGenerateCandidateInput,
    AAAGenerateCandidateTool,
)


# ---------------------------------------------------------------------------
# P4 – Extended field acceptance
# ---------------------------------------------------------------------------


def test_candidate_input_accepts_new_fields() -> None:
    data: dict[str, Any] = {
        "title": "Test arch",
        "summary": "Test summary",
        "components": [{"name": "ACA", "role": "compute"}],
        "alternatives_rejected": [{"name": "AKS", "reason": "too complex"}],
        "waf_mapping": {"reliability": "covered", "security": "partial"},
        "decision_evidence_map": [
            {"decision_id": "d1", "service_choice": "ACA", "confidence": "high"}
        ],
    }
    inp = AAAGenerateCandidateInput(**data)
    assert inp.components[0]["name"] == "ACA"
    assert inp.alternatives_rejected[0]["name"] == "AKS"
    assert inp.waf_mapping["reliability"] == "covered"
    assert inp.decision_evidence_map[0]["decision_id"] == "d1"


def test_candidate_input_backward_compat() -> None:
    """Old format without new fields must still work."""
    data: dict[str, Any] = {"title": "Old arch", "summary": "Old summary"}
    inp = AAAGenerateCandidateInput(**data)
    assert inp.components == []
    assert inp.service_choices == []
    assert inp.alternatives_rejected == []
    assert inp.tradeoffs == []
    assert inp.risks == []
    assert inp.waf_mapping == {}
    assert inp.nfr_mapping == {}
    assert inp.cost_drivers == []
    assert inp.operational_considerations == []
    assert inp.security_controls == []
    assert inp.implementation_phases == []
    assert inp.adr_candidates == []
    assert inp.decision_evidence_map == []


def test_candidate_input_all_new_fields() -> None:
    """All new optional fields can be set."""
    data: dict[str, Any] = {
        "title": "Full arch",
        "summary": "Full summary",
        "components": [{"name": "ACA", "role": "compute"}, {"name": "CosmosDB", "role": "storage"}],
        "service_choices": [
            {"service": "ACA", "rationale": "serverless simplicity", "evidence": ["doc-1"]}
        ],
        "alternatives_rejected": [{"name": "AKS", "reason": "too complex for team size"}],
        "tradeoffs": ["Higher cold-start latency in exchange for zero-ops scaling"],
        "risks": [{"risk": "vendor lock-in", "mitigation": "containerized workloads"}],
        "waf_mapping": {"reliability": "high", "security": "medium", "cost": "low"},
        "nfr_mapping": {"availability": {"status": "met", "notes": "99.9% SLA"}},
        "cost_drivers": ["CosmosDB RUs", "ACA replicas"],
        "operational_considerations": ["Blue-green deployment via ACA revisions"],
        "security_controls": ["Managed Identity", "Private Endpoints"],
        "implementation_phases": [
            {"phase": 1, "scope": "Core compute + storage", "duration_weeks": 4}
        ],
        "adr_candidates": [{"title": "Choose ACA over AKS", "status": "draft"}],
        "decision_evidence_map": [
            {
                "decision_id": "dec-1",
                "service_choice": "ACA",
                "requirement_ids": ["req-1"],
                "evidence_packet_ids": ["research-packet-1"],
                "source_citations": ["https://learn.microsoft.com/azure/container-apps"],
                "confidence": "high",
            }
        ],
    }
    inp = AAAGenerateCandidateInput(**data)
    assert len(inp.components) == 2
    assert inp.tradeoffs[0].startswith("Higher cold-start")
    assert inp.waf_mapping["cost"] == "low"
    assert inp.decision_evidence_map[0]["confidence"] == "high"


def test_candidate_input_camelcase_aliases() -> None:
    """Fields can also be provided in camelCase (alias)."""
    data: dict[str, Any] = {
        "title": "Alias arch",
        "summary": "Alias summary",
        "wafMapping": {"reliability": "covered"},
        "nfrMapping": {"availability": {"status": "met"}},
        "costDrivers": ["CosmosDB RUs"],
        "alternativesRejected": [{"name": "VM", "reason": "not cloud-native"}],
        "decisionEvidenceMap": [
            {"decision_id": "d2", "service_choice": "AppService", "confidence": "medium"}
        ],
    }
    inp = AAAGenerateCandidateInput.model_validate(data)
    assert inp.waf_mapping["reliability"] == "covered"
    assert inp.cost_drivers[0] == "CosmosDB RUs"
    assert inp.alternatives_rejected[0]["name"] == "VM"
    assert inp.decision_evidence_map[0]["service_choice"] == "AppService"


# ---------------------------------------------------------------------------
# P4 – Tool _run output includes new fields
# ---------------------------------------------------------------------------


def test_candidate_tool_run_includes_new_fields() -> None:
    tool = AAAGenerateCandidateTool()
    payload = {
        "title": "Microservices on ACA",
        "summary": "Event-driven microservices using Azure Container Apps",
        "components": [{"name": "ACA", "role": "compute"}],
        "waf_mapping": {"reliability": "high"},
        "tradeoffs": ["cold-start vs zero-ops"],
        "risks": [{"risk": "vendor lock-in", "mitigation": "containers"}],
    }
    result = tool._run(payload=payload)
    assert "AAA_STATE_UPDATE" in result
    # Extract JSON block
    json_block = result.split("```json\n")[1].split("\n```")[0]
    parsed = json.loads(json_block)
    candidate = parsed["candidateArchitectures"][0]
    assert candidate["components"] == [{"name": "ACA", "role": "compute"}]
    assert candidate["wafMapping"] == {"reliability": "high"}
    assert candidate["tradeoffs"] == ["cold-start vs zero-ops"]
    assert candidate["risks"] == [{"risk": "vendor lock-in", "mitigation": "containers"}]


def test_candidate_tool_run_empty_new_fields_not_in_output_when_empty() -> None:
    """When new fields are empty, they are still serialized (as empty lists/dicts)."""
    tool = AAAGenerateCandidateTool()
    payload = {"title": "Minimal arch", "summary": "Minimal summary"}
    result = tool._run(payload=payload)
    json_block = result.split("```json\n")[1].split("\n```")[0]
    parsed = json.loads(json_block)
    candidate = parsed["candidateArchitectures"][0]
    # Empty defaults should be present
    assert "components" in candidate
    assert candidate["components"] == []
    assert "wafMapping" in candidate
    assert candidate["wafMapping"] == {}


# ---------------------------------------------------------------------------
# P7 – decision_evidence_map traceability
# ---------------------------------------------------------------------------


def test_decision_evidence_map_field_present() -> None:
    data: dict[str, Any] = {
        "title": "Traced arch",
        "summary": "Architecture with full traceability",
        "service_choices": [{"service": "ACA", "rationale": "scale to zero"}],
        "decision_evidence_map": [
            {
                "decision_id": "dec-aca",
                "service_choice": "ACA",
                "requirement_ids": ["req-perf-1"],
                "evidence_packet_ids": ["research-packet-1"],
                "source_citations": ["https://learn.microsoft.com/azure/container-apps/scale-app"],
                "confidence": "high",
            }
        ],
    }
    inp = AAAGenerateCandidateInput(**data)
    assert len(inp.decision_evidence_map) == 1
    entry = inp.decision_evidence_map[0]
    assert entry["decision_id"] == "dec-aca"
    assert entry["evidence_packet_ids"] == ["research-packet-1"]
    assert entry["confidence"] == "high"


def test_candidate_tool_warns_when_service_choices_without_evidence(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Tool should log a warning when service_choices provided but decision_evidence_map is empty."""
    tool = AAAGenerateCandidateTool()
    payload = {
        "title": "No-evidence arch",
        "summary": "Architecture with service choices but no evidence map",
        "service_choices": [{"service": "ACA", "rationale": "scale to zero"}],
        "decision_evidence_map": [],
    }
    with caplog.at_level(logging.WARNING, logger="app"):
        result = tool._run(payload=payload)
    assert "AAA_STATE_UPDATE" in result
    assert any("decision_evidence_map" in record.message.lower() for record in caplog.records)


def test_candidate_tool_no_warning_when_evidence_matches_service_choices(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """No warning when decision_evidence_map covers service_choices."""
    tool = AAAGenerateCandidateTool()
    payload = {
        "title": "Evidenced arch",
        "summary": "Architecture with full evidence",
        "service_choices": [{"service": "ACA", "rationale": "scale to zero"}],
        "decision_evidence_map": [
            {
                "decision_id": "dec-aca",
                "service_choice": "ACA",
                "confidence": "high",
            }
        ],
    }
    with caplog.at_level(logging.WARNING, logger="app"):
        result = tool._run(payload=payload)
    assert "AAA_STATE_UPDATE" in result
    # No missing evidence warning expected
    missing_evidence_warnings = [
        r for r in caplog.records if "decision_evidence_map" in r.message.lower()
    ]
    assert missing_evidence_warnings == []


# ---------------------------------------------------------------------------
# P4 – CandidateArchitecture model in aaa_state_models
# ---------------------------------------------------------------------------


def test_candidate_architecture_state_model_accepts_new_fields() -> None:
    """CandidateArchitecture state model accepts new fields (backward-compat via extra=allow)."""
    from app.agents_system.services.aaa_state_models import CandidateArchitecture

    data: dict[str, Any] = {
        "id": "cand-1",
        "title": "State model test",
        "summary": "Test state model",
        "components": [{"name": "ACA", "role": "compute"}],
        "waf_mapping": {"reliability": "high"},
        "tradeoffs": ["cold-start"],
        "decision_evidence_map": [{"decision_id": "d1", "service_choice": "ACA", "confidence": "high"}],
    }
    cand = CandidateArchitecture.model_validate(data)
    assert cand.components[0]["name"] == "ACA"
    assert cand.waf_mapping == {"reliability": "high"}
    assert cand.tradeoffs == ["cold-start"]


def test_candidate_architecture_state_model_backward_compat() -> None:
    """Old-format candidate (no new fields) still parses correctly."""
    from app.agents_system.services.aaa_state_models import CandidateArchitecture

    data: dict[str, Any] = {
        "id": "old-cand",
        "title": "Old candidate",
        "summary": "Old summary",
        "assumptionIds": ["a-1"],
        "diagramIds": [],
        "sourceCitations": [],
    }
    cand = CandidateArchitecture.model_validate(data)
    assert cand.id == "old-cand"
    assert cand.components == []
    assert cand.waf_mapping == {}
    assert cand.decision_evidence_map == []
