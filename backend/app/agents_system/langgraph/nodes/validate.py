"""Dedicated stage worker for validate runtime execution."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from app.agents_system.services.waf_evaluator import WAFEvaluatorService
from app.agents_system.services.waf_findings_worker import WAFFindingsWorker
from app.features.agent.infrastructure.tools.aaa_validation_tool import AAARunValidationTool

from ..state import GraphState

logger = logging.getLogger(__name__)

_ACTIONABLE_STATUSES = frozenset({"open", "in_progress"})


async def execute_validate_stage_worker_node(
    state: GraphState,
    *,
    evaluator: WAFEvaluatorService | None = None,
    findings_worker: WAFFindingsWorker | None = None,
    validation_tool: AAARunValidationTool | None = None,
) -> dict[str, Any]:
    """Run the validate stage through deterministic evaluation + findings synthesis."""
    if state.get("next_stage") != "validate":
        return {}

    project_state = _project_state_from_graph_state(state)
    evaluator_service = evaluator or WAFEvaluatorService()
    findings_service = findings_worker or WAFFindingsWorker()
    tool = validation_tool or AAARunValidationTool()

    try:
        evaluator_result = evaluator_service.evaluate({"current_project_state": project_state})
        summary = _evaluation_summary(evaluator_result)
        evaluated_items = int(summary.get("evaluatedItems") or 0)
        source_count = int(summary.get("sourceCount") or 0)

        if evaluated_items <= 0 or source_count <= 0:
            logger.info(
                "Skipping validate stage worker due to insufficient input (evaluated_items=%s, source_count=%s)",
                evaluated_items,
                source_count,
            )
            return {
                "agent_output": (
                    "Validation skipped: insufficient checklist or architecture evidence. "
                    "Add at least one WAF checklist item plus supporting architecture context before re-running validation."
                ),
                "intermediate_steps": [],
                "success": True,
                "error": None,
                "validation_execution_artifact": {
                    "status": "skipped",
                    "reason": "insufficient_input",
                    "evaluated_items": evaluated_items,
                    "source_count": source_count,
                },
            }

        findings_payload = await findings_service.generate_findings(
            evaluator_result=evaluator_result,
            architecture_state=project_state,
        )
        findings = findings_payload.get("findings")
        waf_evaluations = findings_payload.get("wafEvaluations")
        findings_count = len(findings) if isinstance(findings, list) else 0
        waf_evaluations_count = len(waf_evaluations) if isinstance(waf_evaluations, list) else 0
        actionable_items = _count_actionable_items(evaluator_result)

        if findings_count <= 0 and waf_evaluations_count <= 0:
            logger.info(
                "Validate stage worker found no actionable deltas (evaluated_items=%s, actionable_items=%s)",
                evaluated_items,
                actionable_items,
            )
            return {
                "agent_output": (
                    "Validation complete. Deterministic WAF evaluation found no actionable findings or checklist deltas for this turn."
                ),
                "intermediate_steps": [],
                "success": True,
                "error": None,
                "validation_execution_artifact": {
                    "status": "completed",
                    "evaluated_items": evaluated_items,
                    "actionable_items": actionable_items,
                    "findings_generated": findings_count,
                    "waf_evaluations_generated": waf_evaluations_count,
                },
            }

        agent_output = tool._run(payload=findings_payload)
        success = not str(agent_output).strip().startswith("ERROR:")
        error = None if success else str(agent_output).removeprefix("ERROR: ").strip() or str(agent_output)
        return {
            "agent_output": agent_output,
            "intermediate_steps": [],
            "success": success,
            "error": error,
            "validation_execution_artifact": {
                "status": "completed",
                "evaluated_items": evaluated_items,
                "actionable_items": actionable_items,
                "findings_generated": findings_count,
                "waf_evaluations_generated": waf_evaluations_count,
            },
        }
    except Exception as exc:
        logger.error("validate stage worker failed: %s", exc, exc_info=True)
        error_message = f"Validate stage worker failed: {exc!s}"
        return {
            "agent_output": f"ERROR: {error_message}",
            "intermediate_steps": [],
            "success": False,
            "error": error_message,
            "validation_execution_artifact": {
                "status": "failed",
                "reason": "runtime_error",
            },
        }


def _project_state_from_graph_state(state: GraphState) -> dict[str, Any]:
    project_state = state.get("current_project_state")
    if isinstance(project_state, Mapping):
        return dict(project_state)
    return {}


def _evaluation_summary(evaluator_result: Mapping[str, Any]) -> Mapping[str, Any]:
    summary = evaluator_result.get("summary")
    if isinstance(summary, Mapping):
        return summary
    return {}


def _count_actionable_items(evaluator_result: Mapping[str, Any]) -> int:
    raw_items = evaluator_result.get("items")
    if not isinstance(raw_items, list):
        return 0
    return sum(
        1
        for item in raw_items
        if isinstance(item, Mapping)
        and str(item.get("status") or "").strip().lower() in _ACTIONABLE_STATUSES
    )
