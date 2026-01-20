"""AAA validation tool.

User Story 4 (T030/T031): Provide a deterministic tool that lets the agent
persist validation findings and WAF checklist evaluation updates into ProjectState
via the existing state update pipeline.

Design notes:
- This tool does NOT call external services.
- Findings and checklist updates are append-only. WAF coverage is tracked via
  evaluation entries (no scalar overwrite), which aligns with the project's
  no-overwrite merge rules.
- Citations are required for findings (SC-011).
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Type, Union

from langchain.tools import BaseTool
from pydantic import BaseModel, Field


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


FindingSeverity = Literal["low", "medium", "high", "critical"]
WafCoverageStatus = Literal["covered", "partial", "notCovered"]


class ValidationFindingInput(BaseModel):
    title: str = Field(min_length=1, description="Short finding title")
    severity: FindingSeverity = Field(description="Finding severity")
    description: str = Field(min_length=1, description="What is wrong / risk")
    remediation: str = Field(min_length=1, description="Recommended remediation")

    wafPillar: Optional[str] = Field(
        default=None,
        description="WAF pillar this finding maps to (best-effort)",
    )
    wafTopic: Optional[str] = Field(
        default=None,
        description="WAF topic / checklist item name this finding maps to (best-effort)",
    )

    relatedRequirementIds: List[str] = Field(
        default_factory=list,
        description="Requirement IDs impacted by this finding (best-effort)",
    )
    relatedDiagramIds: List[str] = Field(
        default_factory=list,
        description="Diagram IDs impacted by this finding (best-effort)",
    )
    relatedAdrIds: List[str] = Field(
        default_factory=list,
        description="ADR IDs impacted by this finding (best-effort)",
    )
    relatedMindMapNodeIds: List[str] = Field(
        default_factory=list,
        description="Mind map node IDs impacted by this finding (best-effort)",
    )

    sourceCitations: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="SourceCitation[] objects (must include at least one)",
    )


class WafChecklistEvaluationInput(BaseModel):
    """Append-only evaluation entry for a WAF checklist item."""

    itemId: str = Field(
        min_length=1,
        description="Stable WAF checklist item id (if unknown, create a new stable id)",
    )
    pillar: str = Field(min_length=1, description="WAF pillar")
    topic: str = Field(min_length=1, description="WAF topic/title")

    status: WafCoverageStatus = Field(description="covered|partial|notCovered")
    evidence: str = Field(
        min_length=1,
        description="Short evidence summary justifying the status",
    )

    relatedFindingIds: List[str] = Field(
        default_factory=list,
        description="Finding IDs that provide evidence for this evaluation",
    )
    sourceCitations: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="SourceCitation[] objects used for this evaluation (recommended)",
    )


class AAARunValidationInput(BaseModel):
    findings: List[ValidationFindingInput] = Field(
        default_factory=list,
        description="Findings discovered during validation",
    )

    wafEvaluations: List[WafChecklistEvaluationInput] = Field(
        default_factory=list,
        description="Append-only WAF checklist evaluations with evidence links",
    )


class AAARunValidationToolInput(BaseModel):
    """Raw tool payload for validation."""

    payload: Union[str, Dict[str, Any]] = Field(
        description="A JSON object (or JSON string) matching AAARunValidationInput."
    )


class AAARunValidationTool(BaseTool):
    name: str = "aaa_record_validation_results"
    description: str = (
        "Record validation findings and WAF checklist evaluation updates. "
        "Returns an AAA_STATE_UPDATE JSON block that can be merged into ProjectState without overwriting. "
        "Use after consulting reference docs/MCP and include sourceCitations."
    )

    args_schema: Type[BaseModel] = AAARunValidationToolInput

    def _run(
        self,
        payload: Union[str, Dict[str, Any], None] = None,
        *args: Any,
        **kwargs: Any,
    ) -> str:
        # Accept positional dict payload for compat
        if payload is None and args:
            first = args[0]
            if isinstance(first, dict):
                payload = first

        if payload is None:
            # Accept direct keyword args for backwards compatibility with tests
            if "payload" in kwargs:
                payload = kwargs["payload"]
            elif kwargs:
                payload = kwargs
            else:
                raise ValueError("Missing payload for aaa_record_validation_results")

        if isinstance(payload, str):
            try:
                data = json.loads(payload.strip())
            except json.JSONDecodeError as exc:
                raise ValueError("Invalid JSON payload for validation results.") from exc
        else:
            data = payload

        try:
            args = AAARunValidationInput.model_validate(data)
        except Exception as exc:
            return f"ERROR: Validation failed for AAARunValidationInput: {str(exc)}"

        findings = args.findings
        wafEvaluations = args.wafEvaluations

        finding_items: List[Dict[str, Any]] = []

        for f_obj in findings or []:
            f = f_obj.model_dump() if hasattr(f_obj, "model_dump") else f_obj
            citations = f.get("sourceCitations") or []
            if not citations:
                raise ValueError(
                    "Each finding must include at least one source citation (SC-011)."
                )

            finding_id = str(uuid.uuid4())
            finding_items.append(
                {
                    "id": finding_id,
                    "title": str(f.get("title") or "").strip(),
                    "severity": str(f.get("severity") or "").strip(),
                    "description": str(f.get("description") or "").strip(),
                    "remediation": str(f.get("remediation") or "").strip(),
                    "wafPillar": (str(f.get("wafPillar") or "").strip() or None),
                    "wafTopic": (str(f.get("wafTopic") or "").strip() or None),
                    "relatedRequirementIds": [
                        str(v).strip()
                        for v in (f.get("relatedRequirementIds") or [])
                        if str(v).strip()
                    ],
                    "relatedDiagramIds": [
                        str(v).strip()
                        for v in (f.get("relatedDiagramIds") or [])
                        if str(v).strip()
                    ],
                    "relatedAdrIds": [
                        str(v).strip()
                        for v in (f.get("relatedAdrIds") or [])
                        if str(v).strip()
                    ],
                    "relatedMindMapNodeIds": [
                        str(v).strip()
                        for v in (f.get("relatedMindMapNodeIds") or [])
                        if str(v).strip()
                    ],
                    "sourceCitations": citations,
                    "createdAt": _now_iso(),
                }
            )

        waf_items_by_id: Dict[str, Dict[str, Any]] = {}
        for evaluation_obj in wafEvaluations or []:
            evaluation = evaluation_obj.model_dump() if hasattr(evaluation_obj, "model_dump") else evaluation_obj
            item_id = str(evaluation.get("itemId") or "").strip()
            if not item_id:
                raise ValueError("WAF evaluation requires itemId")

            pillar = str(evaluation.get("pillar") or "").strip()
            topic = str(evaluation.get("topic") or "").strip()
            status = str(evaluation.get("status") or "").strip()
            evidence = str(evaluation.get("evidence") or "").strip()
            if not (pillar and topic and status and evidence):
                raise ValueError(
                    "WAF evaluation requires pillar, topic, status, and evidence."
                )

            eval_entry: Dict[str, Any] = {
                "id": str(uuid.uuid4()),
                "status": status,
                "evidence": evidence,
                "relatedFindingIds": [
                    str(v).strip()
                    for v in (evaluation.get("relatedFindingIds") or [])
                    if str(v).strip()
                ],
                "sourceCitations": evaluation.get("sourceCitations") or [],
                "createdAt": _now_iso(),
            }

            item = waf_items_by_id.get(item_id)
            if item is None:
                item = {
                    "id": item_id,
                    "pillar": pillar,
                    "topic": topic,
                    "evaluations": [eval_entry],
                }
                waf_items_by_id[item_id] = item
            else:
                item.setdefault("evaluations", []).append(eval_entry)

        updates: Dict[str, Any] = {}
        if finding_items:
            updates["findings"] = finding_items
        if waf_items_by_id:
            updates["wafChecklist"] = {"items": list(waf_items_by_id.values())}

        payload_json = json.dumps(updates, ensure_ascii=False, indent=2)

        return (
            f"Recorded validation results at {_now_iso()} (findings={len(finding_items)}, wafEvaluations={len(wafEvaluations or [])}).\n"
            "\n"
            "AAA_STATE_UPDATE\n"
            "```json\n"
            f"{payload_json}\n"
            "```"
        )

    async def _arun(self, **kwargs: Any) -> str:
        return self._run(**kwargs)


def create_validation_tools() -> List[BaseTool]:
    return [AAARunValidationTool()]
