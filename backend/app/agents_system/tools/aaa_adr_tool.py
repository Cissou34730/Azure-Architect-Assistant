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
from typing import Any, Literal

from langchain.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic.alias_generators import to_camel


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


ADRStatus = Literal["draft", "accepted", "rejected", "superseded"]
ADRAction = Literal["create", "revise", "supersede"]


class AAAManageAdrInput(BaseModel):
    """Input schema for creating or revising an ADR."""

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

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

    related_requirement_ids: list[str] = Field(
        default_factory=list,
        description="Requirement IDs that this ADR is based on (must be non-empty)",
    )
    related_mind_map_node_ids: list[str] = Field(
        default_factory=list,
        description="Mind map node IDs tied to this ADR (best-effort)",
    )

    related_diagram_ids: list[str] = Field(
        default_factory=list,
        description="Diagram IDs linked to this ADR (best-effort)",
    )
    related_waf_evidence_ids: list[str] = Field(
        default_factory=list,
        description=(
            "WAF evidence identifiers (e.g., checklist item ids) linked to this ADR (best-effort)"
        ),
    )
    missing_evidence_reason: str | None = Field(
        default=None,
        description=(
            "Required when no relatedDiagramIds and no relatedWafEvidenceIds are provided. "
            "Explains why evidence links are not available yet (SC-005)."
        ),
    )

    source_citations: list[dict[str, Any]] = Field(
        default_factory=list,
        description="SourceCitation[] objects (must include at least one)",
    )

    supersedes_adr_id: str | None = Field(
        default=None,
        description="When action is 'revise' or 'supersede', the ADR id being superseded.",
    )


class AAAManageAdrToolInput(BaseModel):
    """Raw tool payload.

    LangChain's ReAct agent supplies `Action Input:` as a string. If we keep the
    structured args schema directly, BaseTool will map the entire JSON string
    into the first field and Pydantic validation fails. We instead accept a
    single payload and validate after JSON parsing.
    """

    payload: str | dict[str, Any] = Field(
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

    args_schema: type[BaseModel] = AAAManageAdrToolInput

    def _run(
        self,
        payload: str | dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            raw_data = self._parse_payload(payload, **kwargs)
            args = self._validate_args(raw_data)
            adr_id = str(uuid.uuid4())
            adr = self._build_adr(adr_id, args)
            trace_links = self._build_trace_links(adr_id, args)

            updates = {
                "adrs": [adr],
                "traceabilityLinks": trace_links,
            }

            payload_str = json.dumps(updates, ensure_ascii=False, indent=2)
            verb = self._get_verb(args.action)

            return (
                f"{verb} ADR '{adr['title']}' (id={adr_id}) at {_now_iso()}.\n"
                "\n"
                "AAA_STATE_UPDATE\n"
                "```json\n"
                f"{payload_str}\n"
                "```"
            )
        except Exception as exc:  # noqa: BLE001
            # Return error to agent as string rather than raising to caller
            return f"ERROR: {exc!s}"

    def _parse_payload(
        self, payload: str | dict[str, Any] | None, **kwargs: Any
    ) -> dict[str, Any]:
        if payload is None:
            payload = kwargs.get("payload") or kwargs.get("tool_input")
            if payload is None:
                raise ValueError("Missing payload for aaa_manage_adr")

        if isinstance(payload, str):
            try:
                return json.loads(payload.strip())
            except json.JSONDecodeError as exc:
                raise ValueError(
                    "Invalid JSON payload. Provide a JSON object in Action Input."
                ) from exc
        if isinstance(payload, dict):
            return payload
        raise ValueError("Invalid payload type for aaa_manage_adr")

    def _validate_args(self, data: dict[str, Any]) -> AAAManageAdrInput:
        try:
            args = AAAManageAdrInput.model_validate(data)
            self._check_constraints(args)
            return args
        except ValidationError as exc:
            missing = []
            for err in exc.errors():
                if err["type"] == "missing":
                    loc = ".".join(str(i) for i in err["loc"])
                    missing.append(loc)
            hint = (
                "Validation failed. Missing or invalid fields: "
                + (", ".join(missing) if missing else "see schema")
                + ". Ensure you provide action, title, context, decision, consequences, relatedRequirementIds, sourceCitations."
            )
            # Re-wrap as ValueError to be caught by _run
            raise ValueError(hint) from exc

    def _check_constraints(self, args: AAAManageAdrInput) -> None:
        if not args.related_requirement_ids:
            raise ValueError(
                "ADR must link to at least one requirement id (SC-005). Provide relatedRequirementIds."
            )
        if not args.source_citations:
            raise ValueError(
                "ADR must include at least one source citation (SC-011). Provide sourceCitations."
            )
        if (
            not args.related_diagram_ids
            and not args.related_waf_evidence_ids
            and not (args.missing_evidence_reason or "").strip()
        ):
            raise ValueError(
                "When no diagram/WAF evidence links are available, you must provide missingEvidenceReason (SC-005)."
            )

        if args.action in ("revise", "supersede") and not (args.supersedes_adr_id or "").strip():
            raise ValueError(
                "action='revise' or 'supersede' requires supersedesAdrId (the prior ADR id)."
            )

    def _build_adr(self, adr_id: str, args: AAAManageAdrInput) -> dict[str, Any]:
        adr: dict[str, Any] = {
            "id": adr_id,
            "title": args.title.strip(),
            "status": args.status,
            "context": args.context.strip(),
            "decision": args.decision.strip(),
            "consequences": args.consequences.strip(),
            "relatedRequirementIds": [r.strip() for r in args.related_requirement_ids],
            "relatedMindMapNodeIds": [m.strip() for m in args.related_mind_map_node_ids],
            "sourceCitations": args.source_citations,
            "createdAt": _now_iso(),
        }
        if args.supersedes_adr_id:
            adr["supersedesAdrId"] = args.supersedes_adr_id
        if args.related_diagram_ids:
            adr["relatedDiagramIds"] = [d.strip() for d in args.related_diagram_ids]
        if args.related_waf_evidence_ids:
            adr["relatedWafEvidenceIds"] = [w.strip() for w in args.related_waf_evidence_ids]
        if args.missing_evidence_reason:
            adr["missingEvidenceReason"] = args.missing_evidence_reason.strip()
        return adr

    def _build_trace_links(self, adr_id: str, args: AAAManageAdrInput) -> list[dict[str, Any]]:
        links = []

        def _add(t: str, tid: str) -> None:
            links.append(
                {
                    "id": str(uuid.uuid4()),
                    "fromType": "adr",
                    "fromId": adr_id,
                    "toType": t,
                    "toId": tid,
                }
            )

        for rid in args.related_requirement_ids:
            _add("requirement", rid.strip())
        for nid in args.related_mind_map_node_ids:
            _add("mindMapNode", nid.strip())
        for did in args.related_diagram_ids:
            _add("diagram", did.strip())
        for wid in args.related_waf_evidence_ids:
            _add("wafEvidence", wid.strip())
        return links

    def _get_verb(self, action: ADRAction) -> str:
        return {
            "create": "Created",
            "revise": "Created revised",
            "supersede": "Created superseding",
        }.get(action, "Created")

    async def _arun(
        self,
        payload: str | dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        return self._run(payload=payload, **kwargs)

def create_adr_tools() -> list[BaseTool]:
    return [AAAManageAdrTool()]

