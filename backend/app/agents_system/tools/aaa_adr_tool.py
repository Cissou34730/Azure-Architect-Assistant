"""AAA ADR tool.

User Story 3 (T027/T049): Provide a deterministic tool that lets the agent
create ADR artifacts (append-only) with citations and traceability links.

Important constraints:
- This tool does NOT call external services.
- State updates are merged with a no-overwrite strategy, so ADR updates are
  represented as new ADR versions that reference prior ADRs via `supersedesAdrId`.
- SC-005: ADR must link to ≥1 originating requirement. Diagram/WAF linkage is
  best-effort; if missing, an explicit reason must be recorded.
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


ADRStatus = Literal["draft", "accepted", "rejected", "superseded"]
ADRAction = Literal["create", "revise", "supersede"]


class AAAManageAdrInput(BaseModel):
    """Input schema for creating or revising an ADR."""

    action: ADRAction = Field(
        description=(
            "Action to perform. 'create' creates a new ADR. 'revise' creates a new ADR version "
            "that supersedes an existing ADR. 'supersede' creates a new ADR that supersedes an "
            "existing ADR (used when a decision is reversed)."
        )
    )

    title: str = Field(min_length=1, description="Short ADR title")
    status: ADRStatus = Field(
        default="draft",
        description="ADR status (draft/accepted/rejected/superseded)",
    )
    context: str = Field(min_length=1, description="Decision context")
    decision: str = Field(min_length=1, description="The decision")
    consequences: str = Field(min_length=1, description="Consequences/tradeoffs")

    relatedRequirementIds: List[str] = Field(
        default_factory=list,
        description="Requirement IDs that this ADR is based on (must be non-empty)",
    )
    relatedMindMapNodeIds: List[str] = Field(
        default_factory=list,
        description="Mind map node IDs tied to this ADR (best-effort)",
    )

    relatedDiagramIds: List[str] = Field(
        default_factory=list,
        description="Diagram IDs linked to this ADR (best-effort)",
    )
    relatedWafEvidenceIds: List[str] = Field(
        default_factory=list,
        description=(
            "WAF evidence identifiers (e.g., checklist item ids) linked to this ADR (best-effort)"
        ),
    )
    missingEvidenceReason: Optional[str] = Field(
        default=None,
        description=(
            "Required when no relatedDiagramIds and no relatedWafEvidenceIds are provided. "
            "Explains why evidence links are not available yet (SC-005)."
        ),
    )

    sourceCitations: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="SourceCitation[] objects (must include at least one)",
    )

    supersedesAdrId: Optional[str] = Field(
        default=None,
        description=(
            "When action is 'revise' or 'supersede', the ADR id being superseded."
        ),
    )


class AAAManageAdrToolInput(BaseModel):
    """Raw tool payload.

    LangChain's ReAct agent supplies `Action Input:` as a string. If we keep the
    structured args schema directly, BaseTool will map the entire JSON string
    into the first field and Pydantic validation fails. We instead accept a
    single payload and validate after JSON parsing.
    """

    payload: Union[str, Dict[str, Any]] = Field(
        description=(
            "A JSON object (or JSON string) matching AAAManageAdrInput. Example: "
            "{\"action\":\"create\",\"title\":...,\"context\":...,\"decision\":...,\"consequences\":...,\"relatedRequirementIds\":[...],\"sourceCitations\":[...],...}"
        )
    )


class AAAManageAdrTool(BaseTool):
    name: str = "aaa_manage_adr"
    description: str = (
        "Create an ADR artifact and return an AAA_STATE_UPDATE JSON block. "
        "Use this after gathering sources (kb_search/microsoft_docs_search etc.) so you can include "
        "sourceCitations. ADR updates are append-only: use action=revise/supersede to create a new "
        "ADR version that references an existing ADR via supersedesAdrId."
    )

    args_schema: Type[BaseModel] = AAAManageAdrToolInput

    def _run(
        self, payload: Union[str, Dict[str, Any]]
    ) -> str:
        if isinstance(payload, str):
            raw = payload.strip()
            try:
                data: Dict[str, Any] = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    "Invalid JSON payload for aaa_manage_adr. Provide a JSON object in Action Input."
                ) from exc
        elif isinstance(payload, dict):
            data = payload
        else:
            raise ValueError("Invalid payload type for aaa_manage_adr")

        args = AAAManageAdrInput.model_validate(data)

        action = args.action
        title = args.title
        status = args.status
        context = args.context
        decision = args.decision
        consequences = args.consequences
        relatedRequirementIds = args.relatedRequirementIds
        relatedMindMapNodeIds = args.relatedMindMapNodeIds
        relatedDiagramIds = args.relatedDiagramIds
        relatedWafEvidenceIds = args.relatedWafEvidenceIds
        missingEvidenceReason = args.missingEvidenceReason
        sourceCitations = args.sourceCitations
        supersedesAdrId = args.supersedesAdrId

        requirement_ids = [rid.strip() for rid in (relatedRequirementIds or []) if rid and rid.strip()]
        if not requirement_ids:
            raise ValueError(
                "ADR must link to at least one requirement id (SC-005). Provide relatedRequirementIds." 
            )

        citations = sourceCitations or []
        if not citations:
            raise ValueError(
                "ADR must include at least one source citation (SC-011). Provide sourceCitations." 
            )

        diagram_ids = [did.strip() for did in (relatedDiagramIds or []) if did and did.strip()]
        waf_ids = [wid.strip() for wid in (relatedWafEvidenceIds or []) if wid and wid.strip()]
        if not diagram_ids and not waf_ids:
            reason = (missingEvidenceReason or "").strip()
            if not reason:
                raise ValueError(
                    "When no diagram/WAF evidence links are available, you must provide missingEvidenceReason (SC-005)."
                )
        else:
            reason = (missingEvidenceReason or "").strip() or None

        if action in ("revise", "supersede"):
            if not (supersedesAdrId or "").strip():
                raise ValueError(
                    "action='revise' or 'supersede' requires supersedesAdrId (the prior ADR id)."
                )

        adr_id = str(uuid.uuid4())
        adr: Dict[str, Any] = {
            "id": adr_id,
            "title": title.strip(),
            "status": status,
            "context": context.strip(),
            "decision": decision.strip(),
            "consequences": consequences.strip(),
            "relatedRequirementIds": requirement_ids,
            "relatedMindMapNodeIds": [
                mid.strip() for mid in (relatedMindMapNodeIds or []) if mid and mid.strip()
            ],
            "sourceCitations": citations,
            "createdAt": _now_iso(),
        }

        if action in ("revise", "supersede"):
            adr["supersedesAdrId"] = supersedesAdrId

        if diagram_ids:
            adr["relatedDiagramIds"] = diagram_ids
        if waf_ids:
            adr["relatedWafEvidenceIds"] = waf_ids
        if reason:
            adr["missingEvidenceReason"] = reason

        trace_links: List[Dict[str, Any]] = []

        def _link(to_type: str, to_id: str) -> None:
            trace_links.append(
                {
                    "id": str(uuid.uuid4()),
                    "fromType": "adr",
                    "fromId": adr_id,
                    "toType": to_type,
                    "toId": to_id,
                }
            )

        for req_id in requirement_ids:
            _link("requirement", req_id)
        for node_id in adr.get("relatedMindMapNodeIds", []) or []:
            _link("mindMapNode", node_id)
        for diagram_id in diagram_ids:
            _link("diagram", diagram_id)
        for waf_id in waf_ids:
            _link("wafEvidence", waf_id)

        updates: Dict[str, Any] = {
            "adrs": [adr],
            "traceabilityLinks": trace_links,
        }

        payload = json.dumps(updates, ensure_ascii=False, indent=2)

        verb = {
            "create": "Created",
            "revise": "Created revised",
            "supersede": "Created superseding",
        }.get(action, "Created")

        return (
            f"{verb} ADR '{adr['title']}' (id={adr_id}) at {_now_iso()}.\n"
            "\n"
            "AAA_STATE_UPDATE\n"
            "```json\n"
            f"{payload}\n"
            "```"
        )

    async def _arun(self, **kwargs: Any) -> str:
        return self._run(**kwargs)


def create_adr_tools() -> List[BaseTool]:
    return [AAAManageAdrTool()]
