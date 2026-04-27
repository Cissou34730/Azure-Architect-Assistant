"""Tests for P12: Typed Pydantic contracts for deterministic stage outputs.

TDD: These tests are written first and must FAIL before the implementation exists.
"""
from __future__ import annotations

import json
import logging

import pytest

# ---------------------------------------------------------------------------
# Contract imports (will fail until stage_contracts.py is created)
# ---------------------------------------------------------------------------
from app.agents_system.contracts.stage_contracts import (
    AdrDraftOutput,
    ArchitectureDraftOutput,
    ClarificationPlanOutput,
    RequirementsExtractionOutput,
    ValidationOutput,
    _parse_and_validate_output,
)


# ---------------------------------------------------------------------------
# RequirementsExtractionOutput
# ---------------------------------------------------------------------------


def test_requirements_extraction_output_valid_full() -> None:
    data = {
        "functional_requirements": ["FR-001: The system shall authenticate users."],
        "non_functional_requirements": ["NFR-001: 99.9% availability."],
        "constraints": ["Must run in Azure West Europe."],
        "open_questions": ["Which identity provider?"],
    }
    model = RequirementsExtractionOutput.model_validate(data)
    assert model.functional_requirements == ["FR-001: The system shall authenticate users."]
    assert model.non_functional_requirements == ["NFR-001: 99.9% availability."]
    assert model.constraints == ["Must run in Azure West Europe."]
    assert model.open_questions == ["Which identity provider?"]


def test_requirements_extraction_output_defaults_to_empty_lists() -> None:
    model = RequirementsExtractionOutput.model_validate({})
    assert model.functional_requirements == []
    assert model.non_functional_requirements == []
    assert model.constraints == []
    assert model.open_questions == []


def test_requirements_extraction_output_partial_fields() -> None:
    data = {"functional_requirements": ["login", "logout"]}
    model = RequirementsExtractionOutput.model_validate(data)
    assert model.functional_requirements == ["login", "logout"]
    assert model.constraints == []


# ---------------------------------------------------------------------------
# ClarificationPlanOutput
# ---------------------------------------------------------------------------


def test_clarification_plan_output_valid() -> None:
    data = {
        "questions": [
            {
                "question": "What is the expected peak load?",
                "decision_impact": "Sizing and scaling strategy.",
                "default_assumption": "1000 concurrent users.",
            }
        ],
        "proceed_with_defaults": False,
    }
    model = ClarificationPlanOutput.model_validate(data)
    assert len(model.questions) == 1
    assert model.questions[0].question == "What is the expected peak load?"
    assert model.questions[0].decision_impact == "Sizing and scaling strategy."
    assert model.questions[0].default_assumption == "1000 concurrent users."
    assert model.proceed_with_defaults is False


def test_clarification_plan_output_defaults() -> None:
    model = ClarificationPlanOutput.model_validate({})
    assert model.questions == []
    assert model.proceed_with_defaults is False


def test_clarification_plan_question_item_requires_question_field() -> None:
    """A question item with no 'question' key should fail validation."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ClarificationPlanOutput.model_validate(
            {
                "questions": [{"decision_impact": "high", "default_assumption": "none"}],
            }
        )


# ---------------------------------------------------------------------------
# ArchitectureDraftOutput
# ---------------------------------------------------------------------------


def test_architecture_draft_output_valid_full() -> None:
    data = {
        "candidate_name": "Option A – AKS + APIM",
        "summary": "Containerised workload with API gateway.",
        "components": ["AKS", "APIM", "Azure SQL"],
        "trade_offs": ["Higher operational complexity vs. managed PaaS."],
        "risks": ["Team lacks Kubernetes expertise."],
        "waf_highlights": {"reliability": "99.99% SLA with zone-redundant AKS."},
        "next_steps": ["Prototype AKS cluster", "Evaluate APIM policies."],
    }
    model = ArchitectureDraftOutput.model_validate(data)
    assert model.candidate_name == "Option A – AKS + APIM"
    assert "AKS" in model.components
    assert model.waf_highlights["reliability"].startswith("99.99%")


def test_architecture_draft_output_defaults() -> None:
    data = {"candidate_name": "MinimalCandidate", "summary": "TBD"}
    model = ArchitectureDraftOutput.model_validate(data)
    assert model.components == []
    assert model.trade_offs == []
    assert model.risks == []
    assert model.waf_highlights == {}
    assert model.next_steps == []


def test_architecture_draft_output_missing_required_fields() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ArchitectureDraftOutput.model_validate({})


# ---------------------------------------------------------------------------
# ValidationOutput
# ---------------------------------------------------------------------------


def test_validation_output_valid() -> None:
    data = {
        "waf_findings": [{"pillar": "Reliability", "issue": "No zone redundancy."}],
        "severity_breakdown": {"high": 1, "medium": 0, "low": 0},
        "top_issues": ["Enable zone-redundant deployments."],
        "recommendation": "Address the high-severity reliability finding first.",
    }
    model = ValidationOutput.model_validate(data)
    assert len(model.waf_findings) == 1
    assert model.severity_breakdown["high"] == 1
    assert model.recommendation == "Address the high-severity reliability finding first."


def test_validation_output_defaults() -> None:
    model = ValidationOutput.model_validate({})
    assert model.waf_findings == []
    assert model.severity_breakdown == {}
    assert model.top_issues == []
    assert model.recommendation == ""


# ---------------------------------------------------------------------------
# AdrDraftOutput
# ---------------------------------------------------------------------------


def test_adr_draft_output_valid() -> None:
    data = {
        "title": "ADR-001: Use Azure Kubernetes Service for compute",
        "status": "proposed",
        "context": "Need container orchestration at scale.",
        "decision": "Use AKS.",
        "consequences": "Team must invest in Kubernetes skills.",
        "alternatives_considered": ["App Service", "Container Apps"],
    }
    model = AdrDraftOutput.model_validate(data)
    assert model.title == "ADR-001: Use Azure Kubernetes Service for compute"
    assert model.status == "proposed"
    assert "App Service" in model.alternatives_considered


def test_adr_draft_output_defaults() -> None:
    data = {
        "title": "ADR-002: DB choice",
        "context": "ctx",
        "decision": "Use Azure SQL",
        "consequences": "cons",
    }
    model = AdrDraftOutput.model_validate(data)
    assert model.status == "proposed"
    assert model.alternatives_considered == []


def test_adr_draft_output_missing_required_fields() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        AdrDraftOutput.model_validate({})


# ---------------------------------------------------------------------------
# _parse_and_validate_output helper
# ---------------------------------------------------------------------------


def test_parse_and_validate_success() -> None:
    raw = json.dumps(
        {
            "functional_requirements": ["Login"],
            "non_functional_requirements": [],
            "constraints": [],
            "open_questions": [],
        }
    )
    model, fallback = _parse_and_validate_output(raw, RequirementsExtractionOutput)
    assert model is not None
    assert fallback is None
    assert isinstance(model, RequirementsExtractionOutput)
    assert model.functional_requirements == ["Login"]


def test_parse_and_validate_malformed_json(caplog: pytest.LogCaptureFixture) -> None:
    raw = "not valid json {"
    with caplog.at_level(logging.WARNING):
        model, fallback = _parse_and_validate_output(raw, RequirementsExtractionOutput)
    assert model is None
    assert fallback == raw
    assert any("WARNING" in r.levelname or r.levelno >= logging.WARNING for r in caplog.records)


def test_parse_and_validate_schema_mismatch(caplog: pytest.LogCaptureFixture) -> None:
    """Valid JSON but missing required fields for ArchitectureDraftOutput."""
    raw = json.dumps({"unrelated_key": "value"})
    with caplog.at_level(logging.WARNING):
        model, fallback = _parse_and_validate_output(raw, ArchitectureDraftOutput)
    assert model is None
    assert fallback == raw
    assert any("WARNING" in r.levelname or r.levelno >= logging.WARNING for r in caplog.records)


def test_parse_and_validate_returns_none_fallback_on_validation_error() -> None:
    """Valid JSON that violates Pydantic rules returns (None, raw)."""
    raw = json.dumps(
        {
            "questions": [{"decision_impact": "high"}],  # missing required 'question' key
            "proceed_with_defaults": False,
        }
    )
    model, fallback = _parse_and_validate_output(raw, ClarificationPlanOutput)
    assert model is None
    assert fallback == raw


# ---------------------------------------------------------------------------
# Integration: stage worker uses contracts
# ---------------------------------------------------------------------------


def test_validate_node_imports_stage_contracts() -> None:
    """validate.py should import from stage_contracts (integration smoke test)."""
    import importlib

    module = importlib.import_module("app.agents_system.langgraph.nodes.validate")
    # The module must expose _parse_and_validate_output at some level;
    # here we just confirm the import chain works without errors.
    assert module is not None


def test_stage_contracts_module_exports_all_five_contracts() -> None:
    from app.agents_system.contracts import stage_contracts  # noqa: F401

    expected = {
        "RequirementsExtractionOutput",
        "ClarificationPlanOutput",
        "ArchitectureDraftOutput",
        "ValidationOutput",
        "AdrDraftOutput",
        "_parse_and_validate_output",
    }
    for name in expected:
        assert hasattr(stage_contracts, name), f"Missing: {name}"
