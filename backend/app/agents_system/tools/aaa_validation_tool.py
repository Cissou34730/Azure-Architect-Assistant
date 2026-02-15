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
from typing import Any, Literal

from langchain_core.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


FindingSeverity = Literal["low", "medium", "high", "critical"]
WafCoverageStatus = Literal["covered", "partial", "notCovered"]


class ValidationFindingInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    title: str = Field(min_length=1, description="Short finding title")
    severity: FindingSeverity = Field(description="Finding severity")
    description: str = Field(min_length=1, description="What is wrong / risk")
    remediation: str = Field(min_length=1, description="Recommended remediation")

    waf_pillar: str | None = Field(
        default=None,
        description="WAF pillar this finding maps to (best-effort)",
    )
    waf_topic: str | None = Field(
        default=None,
        description="WAF topic / checklist item name this finding maps to (best-effort)",
    )

    related_requirement_ids: list[str] = Field(
        default_factory=list,
        description="Requirement IDs impacted by this finding (best-effort)",
    )
    related_diagram_ids: list[str] = Field(
        default_factory=list,
        description="Diagram IDs impacted by this finding (best-effort)",
    )
    related_adr_ids: list[str] = Field(
        default_factory=list,
        description="ADR IDs impacted by this finding (best-effort)",
    )
    related_mind_map_node_ids: list[str] = Field(
        default_factory=list,
        description="Mind map node IDs impacted by this finding (best-effort)",
    )

    source_citations: list[dict[str, Any]] = Field(
        default_factory=list,
        description="SourceCitation[] objects (must include at least one)",
    )


class WafChecklistEvaluationInput(BaseModel):
    """Append-only evaluation entry for a WAF checklist item."""

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    item_id: str = Field(
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

    related_finding_ids: list[str] = Field(
        default_factory=list,
        description="Finding IDs that provide evidence for this evaluation",
    )
    source_citations: list[dict[str, Any]] = Field(
        default_factory=list,
        description="SourceCitation[] objects used for this evaluation (recommended)",
    )


class AAARunValidationInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    findings: list[ValidationFindingInput] = Field(
        default_factory=list,
        description="Findings discovered during validation",
    )

    waf_evaluations: list[WafChecklistEvaluationInput] = Field(
        default_factory=list,
        description="Append-only WAF checklist evaluations with evidence links",
    )


class AAARunValidationToolInput(BaseModel):
    """Raw tool payload for validation."""

    payload: str | dict[str, Any] = Field(
        description="A JSON object (or JSON string) matching AAARunValidationInput."
    )


class AAARunValidationTool(BaseTool):
    name: str = "aaa_record_validation_results"
    description: str = (
        "Record validation findings and WAF checklist evaluation updates. "
        "Returns an AAA_STATE_UPDATE JSON block that can be merged into ProjectState without overwriting. "
        "Use after consulting reference docs/MCP and include sourceCitations."
    )

    args_schema: type[BaseModel] = AAARunValidationToolInput

    def _run(
        self,
        payload: str | dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        """Execute validation record tool."""
        try:
            raw_data = self._parse_payload(payload, **kwargs)
            args = AAARunValidationInput.model_validate(raw_data)

            if not args.findings and not args.waf_evaluations:
                raise ValueError(
                    "Empty validation payload: provide at least one finding or one wafEvaluation entry."
                )

            finding_items = self._process_findings(args.findings)
            waf_items = self._process_waf_evaluations(args.waf_evaluations)

            updates: dict[str, Any] = {}
            if finding_items:
                updates["findings"] = finding_items
            if waf_items:
                updates["wafChecklist"] = {"items": waf_items}

            payload_json = json.dumps(updates, ensure_ascii=False, indent=2)

            return (
                f"Recorded validation results at {_now_iso()} (findings={len(finding_items)}, wafEvaluations={len(args.waf_evaluations)}).\n"
                "\n"
                "AAA_STATE_UPDATE\n"
                "```json\n"
                f"{payload_json}\n"
                "```"
            )
        except Exception as exc:  # noqa: BLE001
            return f"ERROR: {exc!s}"

    def _parse_payload(self, payload: str | dict[str, Any] | None, **kwargs: Any) -> Any:
        """Extract and parse payload from input."""
        if payload is None:
            payload = kwargs.get("payload") or kwargs.get("tool_input") or kwargs
            if not payload:
                raise ValueError("Missing payload for aaa_record_validation_results")

        if isinstance(payload, str):
            try:
                return json.loads(payload.strip())
            except json.JSONDecodeError as exc:
                raise ValueError("Invalid JSON payload for validation results.") from exc
        return payload

    def _process_findings(self, findings: list[ValidationFindingInput]) -> list[dict[str, Any]]:
        """Normalize findings into state update items."""
        items: list[dict[str, Any]] = []
        for f in findings:
            if not f.source_citations:
                raise ValueError(f"Finding '{f.title}' must include at least one source citation.")
            items.append(
                {
                    "id": str(uuid.uuid4()),
                    "title": f.title.strip(),
                    "severity": f.severity,
                    "description": f.description.strip(),
                    "remediation": f.remediation.strip(),
                    "wafPillar": f.waf_pillar,
                    "wafTopic": f.waf_topic,
                    "relatedRequirementIds": f.related_requirement_ids,
                    "relatedDiagramIds": f.related_diagram_ids,
                    "relatedAdrIds": f.related_adr_ids,
                    "relatedMindMapNodeIds": f.related_mind_map_node_ids,
                    "sourceCitations": f.source_citations,
                    "createdAt": _now_iso(),
                }
            )
        return items

    def _process_waf_evaluations(
        self, evaluations: list[WafChecklistEvaluationInput]
    ) -> list[dict[str, Any]]:
        """Normalize WAF evaluations into grouped checklist items."""
        waf_items_by_id: dict[str, dict[str, Any]] = {}
        for ev in evaluations:
            eval_entry = {
                "id": str(uuid.uuid4()),
                "status": ev.status,
                "evidence": ev.evidence.strip(),
                "relatedFindingIds": ev.related_finding_ids,
                "sourceCitations": ev.source_citations,
                "createdAt": _now_iso(),
            }
            if ev.item_id not in waf_items_by_id:
                waf_items_by_id[ev.item_id] = {
                    "id": ev.item_id,
                    "pillar": ev.pillar.strip(),
                    "topic": ev.topic.strip(),
                    "evaluations": [eval_entry],
                }
            else:
                waf_items_by_id[ev.item_id].setdefault("evaluations", []).append(eval_entry)
        return list(waf_items_by_id.values())

    async def _arun(self, **kwargs: Any) -> str:
        return self._run(**kwargs)


def create_validation_tools() -> list[BaseTool]:
    return [AAARunValidationTool()]

