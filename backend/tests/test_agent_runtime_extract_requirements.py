from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.agents_system.langgraph.nodes import cost_estimator as cost_estimator_module
from app.agents_system.langgraph.nodes import extract_requirements as extract_requirements_module
from app.agents_system.langgraph.nodes import iac_generator as iac_generator_module
from app.agents_system.langgraph.nodes import manage_adr as manage_adr_module
from app.agents_system.langgraph.nodes.cost_estimator import (
    execute_cost_stage_worker_node,
)
from app.agents_system.langgraph.nodes.export import execute_export_stage_worker_node
from app.agents_system.langgraph.nodes.extract_requirements import (
    execute_extract_requirements_node,
)
from app.agents_system.langgraph.nodes.iac_generator import (
    execute_iac_stage_worker_node,
    iac_generator_node,
)
from app.agents_system.langgraph.nodes.manage_adr import (
    execute_manage_adr_stage_worker_node,
)
from app.features.agent.infrastructure.tools.aaa_export_tool import AAAExportTool
from app.features.projects.contracts import ChangeSetStatus, PendingChangeSetContract


class _RequirementsExtractionEntryServiceStub:
    def __init__(self, *, change_set: PendingChangeSetContract) -> None:
        self.change_set = change_set
        self.calls: list[dict[str, object]] = []

    async def extract_pending_requirements(
        self,
        *,
        project_id: str,
        db: object,
        source_message_id: str | None = None,
    ) -> PendingChangeSetContract:
        self.calls.append(
            {
                "project_id": project_id,
                "db": db,
                "source_message_id": source_message_id,
            }
        )
        return self.change_set


def _build_pending_change_set() -> PendingChangeSetContract:
    return PendingChangeSetContract(
        id="cs-req-1",
        project_id="proj-1",
        stage="extract_requirements",
        status=ChangeSetStatus.PENDING,
        created_at=datetime.now(timezone.utc).isoformat(),
        source_message_id=None,
        bundle_summary="Extracted 2 requirement(s) from 2 document(s)",
        proposed_patch={
            "requirements": [
                {"text": "Support SSO for internal users"},
                {"text": "Retain audit logs for 90 days"},
            ]
        },
        artifact_drafts=[],
    )


@pytest.mark.asyncio
async def test_execute_extract_requirements_node_records_pending_bundle(monkeypatch) -> None:
    change_set = _build_pending_change_set()
    service = _RequirementsExtractionEntryServiceStub(change_set=change_set)
    refreshed_state = {"pendingChangeSets": [{"id": change_set.id}]}
    state_loader = AsyncMock(return_value=refreshed_state)
    emitted_events: list[tuple[str, dict[str, object]]] = []

    async def _capture_event(event_type: str, payload: dict[str, object]) -> None:
        emitted_events.append((event_type, payload))

    monkeypatch.setattr(extract_requirements_module, "read_project_state", state_loader)

    result = await execute_extract_requirements_node(
        {
            "project_id": "proj-1",
            "user_message": "Analyze the uploaded documents",
            "next_stage": "extract_requirements",
            "current_project_state": {},
            "event_callback": _capture_event,
        },
        db=object(),
        entry_service=service,
    )

    assert service.calls == [
        {
            "project_id": "proj-1",
            "db": service.calls[0]["db"],
            "source_message_id": None,
        }
    ]
    state_loader.assert_awaited_once()
    assert result["success"] is True
    assert result["handled_by_stage_worker"] is True
    assert result["updated_project_state"] == refreshed_state
    assert "cs-req-1" in result["agent_output"]
    assert "review and approve" in result["agent_output"].lower()
    assert emitted_events == [
        ("message_start", {"role": "assistant"}),
        ("token", {"text": result["agent_output"]}),
    ]


@pytest.mark.asyncio
async def test_execute_extract_requirements_node_skips_other_stages() -> None:
    result = await execute_extract_requirements_node(
        {
            "project_id": "proj-1",
            "user_message": "Continue",
            "next_stage": "clarify",
        },
        db=object(),
        entry_service=_RequirementsExtractionEntryServiceStub(change_set=_build_pending_change_set()),
    )

    assert result == {}


@pytest.mark.asyncio
async def test_execute_extract_requirements_node_surfaces_errors() -> None:
    class _FailingRequirementsExtractionEntryService:
        async def extract_pending_requirements(
            self,
            *,
            project_id: str,
            db: object,
            source_message_id: str | None = None,
        ) -> PendingChangeSetContract:
            raise ValueError("No parsed documents available for extraction")

    result = await execute_extract_requirements_node(
        {
            "project_id": "proj-1",
            "user_message": "Analyze the uploaded documents",
            "next_stage": "extract_requirements",
        },
        db=object(),
        entry_service=_FailingRequirementsExtractionEntryService(),
    )

    assert result["success"] is False
    assert result["error"] == "No parsed documents available for extraction"
    assert result["agent_output"] == "ERROR: No parsed documents available for extraction"


class _ADRManagementWorkerStub:
    def __init__(self, *, change_set: PendingChangeSetContract) -> None:
        self.change_set = change_set
        self.calls: list[dict[str, object]] = []

    async def draft_and_record_pending_change(
        self,
        *,
        project_id: str,
        user_message: str,
        project_state: dict[str, object],
        db: object,
        source_message_id: str | None = None,
    ) -> PendingChangeSetContract:
        self.calls.append(
            {
                "project_id": project_id,
                "user_message": user_message,
                "project_state": project_state,
                "source_message_id": source_message_id,
                "db": db,
            }
        )
        return self.change_set


def _build_adr_pending_change_set() -> PendingChangeSetContract:
    return PendingChangeSetContract(
        id="cs-adr-1",
        project_id="proj-1",
        stage="manage_adr",
        status=ChangeSetStatus.PENDING,
        created_at=datetime.now(timezone.utc).isoformat(),
        source_message_id="msg-1",
        bundle_summary="Drafted one ADR",
        proposed_patch={
            "_adrLifecycle": {
                "action": "create",
                "adrPayload": {"title": "Azure SQL Database"},
            }
        },
        artifact_drafts=[],
    )


@pytest.mark.asyncio
async def test_execute_manage_adr_stage_worker_records_pending_bundle(monkeypatch) -> None:
    change_set = _build_adr_pending_change_set()
    worker = _ADRManagementWorkerStub(change_set=change_set)
    refreshed_state = {"pendingChangeSets": [{"id": change_set.id}]}
    state_loader = AsyncMock(return_value=refreshed_state)
    emitted_events: list[tuple[str, dict[str, object]]] = []

    async def _capture_event(event_type: str, payload: dict[str, object]) -> None:
        emitted_events.append((event_type, payload))

    monkeypatch.setattr(manage_adr_module, "read_project_state", state_loader)

    result = await execute_manage_adr_stage_worker_node(
        {
            "project_id": "proj-1",
            "user_message": "Create an ADR for the database choice.",
            "next_stage": "manage_adr",
            "current_project_state": {},
            "user_message_id": "msg-1",
            "event_callback": _capture_event,
        },
        db=object(),
        worker=worker,
    )

    assert worker.calls == [
        {
            "project_id": "proj-1",
            "user_message": "Create an ADR for the database choice.",
            "project_state": {},
            "source_message_id": "msg-1",
            "db": worker.calls[0]["db"],
        }
    ]
    state_loader.assert_awaited_once()
    assert result["success"] is True
    assert result["handled_by_stage_worker"] is True
    assert result["updated_project_state"] == refreshed_state
    assert "pending change set `cs-adr-1`" in result["agent_output"]
    assert "review and approve" in result["agent_output"].lower()
    assert emitted_events == [
        ("message_start", {"role": "assistant"}),
        ("token", {"text": result["agent_output"]}),
    ]


@pytest.mark.asyncio
async def test_execute_manage_adr_stage_worker_skips_other_stages() -> None:
    result = await execute_manage_adr_stage_worker_node(
        {
            "project_id": "proj-1",
            "user_message": "Continue",
            "next_stage": "clarify",
        },
        db=object(),
        worker=_ADRManagementWorkerStub(change_set=_build_adr_pending_change_set()),
    )

    assert result == {}


class _ExportToolStub:
    def __init__(self, *, output: str) -> None:
        self.output = output
        self.calls: list[dict[str, object]] = []

    def _run(self, **kwargs: object) -> str:
        self.calls.append(dict(kwargs))
        return self.output


@pytest.mark.asyncio
async def test_execute_export_stage_worker_node_uses_dedicated_export_tool() -> None:
    emitted_events: list[tuple[str, dict[str, object]]] = []

    async def _capture_event(event_type: str, payload: dict[str, object]) -> None:
        emitted_events.append((event_type, payload))

    export_tool = _ExportToolStub(output="AAA_EXPORT\n```json\n{\"ok\":true}\n```")

    result = await execute_export_stage_worker_node(
        {
            "project_id": "proj-1",
            "next_stage": "export",
            "current_project_state": {"requirements": [{"id": "req-1"}]},
            "event_callback": _capture_event,
        },
        export_tool=export_tool,
    )

    assert export_tool.calls == [
        {
            "payload": {
                "exportFormat": "json",
                "state": {"requirements": [{"id": "req-1"}]},
                "pretty": True,
                "fileName": "proj-1-aaa-export.json",
            }
        }
    ]
    assert result["success"] is True
    assert result["handled_by_stage_worker"] is True
    assert result["final_answer"] == "AAA_EXPORT\n```json\n{\"ok\":true}\n```"
    assert emitted_events == [
        ("message_start", {"role": "assistant"}),
        ("token", {"text": result["final_answer"]}),
    ]


@pytest.mark.asyncio
async def test_execute_export_stage_worker_node_skips_other_stages() -> None:
    result = await execute_export_stage_worker_node(
        {
            "project_id": "proj-1",
            "next_stage": "clarify",
        }
    )

    assert result == {}


@pytest.mark.asyncio
async def test_execute_export_stage_worker_node_surfaces_errors() -> None:
    export_tool = _ExportToolStub(output="ERROR: Export failed")

    result = await execute_export_stage_worker_node(
        {
            "project_id": "proj-1",
            "next_stage": "export",
            "current_project_state": {},
        },
        export_tool=export_tool,
    )

    assert result["success"] is False
    assert result["error"] == "Export failed"
    assert result["agent_output"] == "ERROR: Export failed"


@pytest.mark.asyncio
async def test_execute_cost_stage_worker_node_reuses_cost_handoff_and_estimator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_prepare_cost_handoff(state):
        captured["handoff_state"] = state
        return {
            "agent_handoff_context": {
                "project_context": "summary",
                "architecture": {"id": "candidate-1"},
                "resource_list": ["Static Web Apps"],
                "region": "eastus",
                "environment": "production",
                "constraints": {},
                "user_request": state.get("user_message", ""),
            },
            "current_agent": "cost_estimator",
        }

    async def fake_cost_estimator_node(state):
        captured["estimator_state"] = state
        return {
            "agent_output": (
                "Recorded cost estimate at 2026-04-08T12:00:00+00:00 (pricingLines=1).\n\n"
                "AAA_STATE_UPDATE\n"
                "```json\n"
                '{\n  "costEstimates": [{"id": "cost-1", "totalMonthlyCost": 42.0}]}\n'
                "```"
            ),
            "intermediate_steps": [],
            "current_agent": "cost_estimator",
            "success": True,
            "error": None,
            "cost_estimate": {"id": "cost-1", "totalMonthlyCost": 42.0},
        }

    monkeypatch.setattr(
        cost_estimator_module,
        "prepare_cost_estimator_handoff",
        fake_prepare_cost_handoff,
    )
    monkeypatch.setattr(
        cost_estimator_module,
        "cost_estimator_node",
        fake_cost_estimator_node,
    )

    result = await execute_cost_stage_worker_node(
        {
            "project_id": "proj-1",
            "user_message": "Estimate the monthly spend",
            "next_stage": "pricing",
            "context_summary": "summary",
            "current_project_state": {
                "candidateArchitectures": [{"id": "candidate-1"}],
            },
        }
    )

    assert captured["handoff_state"] is not None
    estimator_state = captured["estimator_state"]
    assert isinstance(estimator_state, dict)
    assert estimator_state["agent_handoff_context"]["resource_list"] == ["Static Web Apps"]
    assert result["current_agent"] == "cost_estimator"
    assert result["success"] is True
    assert "costEstimates" in result["agent_output"]


@pytest.mark.asyncio
async def test_execute_cost_stage_worker_node_skips_other_stages() -> None:
    result = await execute_cost_stage_worker_node(
        {
            "project_id": "proj-1",
            "user_message": "Continue",
            "next_stage": "clarify",
            "current_project_state": {},
        }
    )

    assert result == {}


@pytest.mark.asyncio
async def test_execute_cost_stage_worker_node_runs_real_cost_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_cost_tool_arun(self, payload=None, **kwargs):  # noqa: ANN001, ARG001
        return (
            "Recorded cost estimate at 2026-04-08T12:00:00+00:00 (pricingLines=1).\n\n"
            "AAA_STATE_UPDATE\n"
            "```json\n"
            "{\n"
            '  "costEstimates": [\n'
            "    {\n"
            '      "id": "cost-1",\n'
            '      "currencyCode": "USD",\n'
            '      "totalMonthlyCost": 42.0,\n'
            '      "lineItems": [{"name": "Azure Functions executions baseline"}],\n'
            '      "pricingGaps": []\n'
            "    }\n"
            "  ]\n"
            "}\n"
            "```\n"
            "AAA_PRICING_LOG\n"
            "```json\n"
            '{"tool":"azure_retail_prices","entries":[{"name":"Azure Functions executions baseline"}]}\n'
            "```"
        )

    monkeypatch.setattr(
        cost_estimator_module.AAAGenerateCostTool,
        "_arun",
        fake_cost_tool_arun,
    )

    result = await execute_cost_stage_worker_node(
        {
            "project_id": "proj-1",
            "user_message": "Estimate the monthly cost for Azure Functions with baseline assumptions.",
            "next_stage": "pricing",
            "current_project_state": {},
        },
        handoff_builder=lambda state: {
            "agent_handoff_context": {
                "project_context": "Functions-based API",
                "architecture": {"description": "Azure Functions backend"},
                "resource_list": ["Azure Functions"],
                "region": "eastus",
                "environment": "production",
                "constraints": {},
                "user_request": state.get("user_message", ""),
            },
            "current_agent": "cost_estimator",
        },
    )

    assert result["current_agent"] == "cost_estimator"
    assert result["success"] is True
    assert result["cost_estimate"] == {
        "id": "cost-1",
        "currencyCode": "USD",
        "totalMonthlyCost": 42.0,
        "lineItems": [{"name": "Azure Functions executions baseline"}],
        "pricingGaps": [],
    }
    assert "AAA_STATE_UPDATE" in result["agent_output"]
    assert "AAA_PRICING_LOG" in result["agent_output"]


@pytest.mark.asyncio
async def test_execute_iac_stage_worker_node_routes_explicit_iac_requests_through_dedicated_runtime() -> None:
    captured: dict[str, object] = {}

    def fake_prepare_iac_handoff(state):
        captured["handoff_state"] = state
        return {
            "agent_handoff_context": {
                "project_context": "summary",
                "architecture": {"id": "candidate-1"},
                "resource_list": ["Storage Account"],
                "constraints": {"regions": ["eastus"]},
                "iac_format": "terraform",
                "user_request": state.get("user_message", ""),
            },
            "current_agent": "iac_generator",
        }

    async def fake_iac_generator(state):
        captured["generator_state"] = state
        return {
            "agent_output": (
                "Recorded IaC artifacts at 2026-04-08T12:00:00+00:00 (iacFiles=1).\n\n"
                "AAA_STATE_UPDATE\n"
                "```json\n"
                '{\n  "iacArtifacts": [{"id": "iac-1"}]}\n'
                "```"
            ),
            "intermediate_steps": [],
            "current_agent": "iac_generator",
            "success": True,
            "error": None,
        }

    result = await execute_iac_stage_worker_node(
        {
            "project_id": "proj-1",
            "user_message": "Generate Terraform code for this architecture",
            "next_stage": "clarify",
            "context_summary": "summary",
            "current_project_state": {
                "candidateArchitectures": [{"id": "candidate-1"}],
            },
        },
        handoff_builder=fake_prepare_iac_handoff,
        generator=fake_iac_generator,
    )

    assert captured["handoff_state"] is not None
    generator_state = captured["generator_state"]
    assert isinstance(generator_state, dict)
    assert generator_state["agent_handoff_context"]["iac_format"] == "terraform"
    assert result["current_agent"] == "iac_generator"
    assert result["success"] is True
    assert "iacArtifacts" in result["agent_output"]


@pytest.mark.asyncio
async def test_execute_iac_stage_worker_node_skips_other_stages() -> None:
    result = await execute_iac_stage_worker_node(
        {
            "project_id": "proj-1",
            "user_message": "Continue",
            "next_stage": "clarify",
            "current_project_state": {},
        }
    )

    assert result == {}


@pytest.mark.asyncio
async def test_iac_generator_node_surfaces_errors_without_main_agent_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        iac_generator_module,
        "PromptLoader",
        lambda: SimpleNamespace(load_prompt=lambda _name: {"system_prompt": "iac prompt"}),
    )
    monkeypatch.setattr(
        iac_generator_module,
        "get_agent_runner",
        AsyncMock(return_value=SimpleNamespace(mcp_client=None, openai_settings=None)),
    )

    async def fake_run_stage_aware_agent(*args, **kwargs):  # noqa: ANN002, ANN003, ARG001
        raise RuntimeError("LLM unavailable")

    monkeypatch.setattr(
        iac_generator_module,
        "run_stage_aware_agent",
        fake_run_stage_aware_agent,
    )

    result = await iac_generator_node(
        {
            "project_id": "proj-1",
            "user_message": "Generate Bicep for this architecture",
            "agent_handoff_context": {
                "architecture": {"id": "candidate-1"},
                "resource_list": ["Storage Account"],
                "iac_format": "bicep",
            },
        }
    )

    assert result["success"] is False
    assert result["current_agent"] == "iac_generator"
    assert result["error"] == "LLM unavailable"
    assert result["agent_output"] == "ERROR: IaC generation failed: LLM unavailable"


@pytest.mark.asyncio
async def test_execute_export_stage_worker_node_emits_real_export_payload() -> None:
    result = await execute_export_stage_worker_node(
        {
            "project_id": "proj-1",
            "next_stage": "export",
            "current_project_state": {
                "requirements": [{"id": "req-1"}],
                "traceabilityLinks": [{"id": "trace-1", "sourceId": "req-1"}],
            },
        }
    )

    payload = _extract_export_payload(result["final_answer"])

    assert result["success"] is True
    assert payload["state"]["traceabilityLinks"] == [{"id": "trace-1", "sourceId": "req-1"}]
    assert len(payload["state"]["mindMapCoverage"]["topics"]) == 13
    assert len(payload["mindmapCoverageScorecard"]["topics"]) == 13


def _extract_export_payload(answer: str) -> dict[str, object]:
    match = re.search(r"AAA_EXPORT\s*\n```json\n(?P<payload>\{.*\})\n```", answer, re.DOTALL)
    assert match is not None
    return json.loads(match.group("payload"))


def test_aaa_export_tool_builds_export_payload_with_scorecard() -> None:
    tool = AAAExportTool()

    response = tool._run(
        payload={
            "fileName": "proj-1-aaa-export.json",
            "state": {
                "requirements": [{"id": "req-1"}],
                "candidateArchitectures": [{"id": "arch-1"}],
                "diagrams": [{"id": "diag-1"}],
                "adrs": [{"id": "adr-1"}],
                "iacArtifacts": [{"id": "iac-1"}],
                "traceabilityLinks": [{"id": "trace-1"}],
                "wafChecklist": {
                    "items": [{"id": "waf-1", "evaluations": [{"status": "fixed"}]}]
                },
                "findings": [{"id": "finding-1", "sourceCitations": [{"id": "src-1"}]}],
            },
        }
    )

    payload = _extract_export_payload(response)

    assert "Exported AAA state to proj-1-aaa-export.json" in response
    assert payload["state"]["traceabilityLinks"] == [{"id": "trace-1"}]
    assert len(payload["state"]["mindMapCoverage"]["topics"]) == 13
    assert len(payload["mindmapCoverageScorecard"]["topics"]) == 13
    assert payload["mindmapCoverageScorecard"]["summary"]["addressed"] >= 1


def test_aaa_export_tool_preserves_existing_mindmap_coverage() -> None:
    tool = AAAExportTool()

    response = tool._run(
        payload={
            "state": {
                "traceabilityLinks": [{"id": "trace-1"}],
                "mindMapCoverage": {
                    "version": "1",
                    "computedAt": "2026-01-01T00:00:00+00:00",
                    "topics": {
                        "1_foundations": {"status": "partial", "confidence": 0.5},
                    },
                },
            }
        }
    )

    payload = _extract_export_payload(response)

    assert payload["state"]["mindMapCoverage"]["topics"]["1_foundations"] == {
        "status": "partial",
        "confidence": 0.5,
    }
    assert (
        payload["mindmapCoverageScorecard"]["topics"]["1_foundations"]["status"]
        == "partial"
    )
