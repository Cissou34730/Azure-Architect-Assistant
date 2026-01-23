"""Pydantic models for AAA artifacts stored inside ProjectState.state.

Phase 2 scope (T007): define minimal typed shapes for AAA state. These models
are used at service boundaries to validate and normalize state reads/writes.

Important: the wider application already stores additional keys in ProjectState;
models in this module must allow unknown fields.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)
from pydantic.alias_generators import to_camel

# Shared configuration for AAA models
_AAA_STRICT_CONFIG = ConfigDict(
    populate_by_name=True, alias_generator=to_camel, extra="forbid"
)
_AAA_LAX_CONFIG = ConfigDict(
    populate_by_name=True, alias_generator=to_camel, extra="allow"
)


class SourceCitationKind(str, Enum):
    reference_document = "referenceDocument"
    mcp = "mcp"


class SourceCitation(BaseModel):
    model_config = _AAA_STRICT_CONFIG

    id: str
    kind: SourceCitationKind
    reference_document_id: str | None = None
    mcp_query_id: str | None = None
    url: str | None = None
    note: str | None = None


class ReferenceDocument(BaseModel):
    model_config = _AAA_STRICT_CONFIG

    id: str
    category: str
    title: str
    url: str | None = None
    accessed_at: str


class MCPQueryPhase(str, Enum):
    architecture = "architecture"
    validation = "validation"
    iac = "iac"
    other = "other"


class MCPQuery(BaseModel):
    model_config = _AAA_STRICT_CONFIG

    id: str
    query_text: str
    phase: MCPQueryPhase
    result_urls: list[str] = Field(default_factory=list)
    selected_snippets: list[str] | None = None
    executed_at: str


class IngestionFailure(BaseModel):
    model_config = _AAA_STRICT_CONFIG

    document_id: str | None = None
    file_name: str
    reason: str


class IngestionStats(BaseModel):
    model_config = _AAA_STRICT_CONFIG

    attempted_documents: int = 0
    parsed_documents: int = 0
    failed_documents: int = 0
    failures: list[IngestionFailure] = Field(default_factory=list)


class IterationEventKind(str, Enum):
    propose = "propose"
    challenge = "challenge"


class IterationEvent(BaseModel):
    model_config = _AAA_STRICT_CONFIG

    id: str
    kind: IterationEventKind
    text: str
    citations: list[SourceCitation] = Field(default_factory=list)
    architect_response_message_id: str | None = None
    created_at: str
    related_artifact_ids: list[str] = Field(default_factory=list)


class TraceabilityLink(BaseModel):
    """A directional trace link between artifacts (for explainability/audit)."""

    model_config = _AAA_LAX_CONFIG

    id: str
    from_type: str
    from_id: str
    to_type: str
    to_id: str


class TraceabilityIssue(BaseModel):
    """Non-blocking traceability verification issue (US6)."""

    model_config = _AAA_LAX_CONFIG

    id: str
    kind: str
    message: str
    link_id: str | None = None
    created_at: str | None = None


ADRStatus = Literal["draft", "accepted", "rejected", "superseded"]


class AdrArtifact(BaseModel):
    """Decision record artifact (US3)."""

    model_config = _AAA_LAX_CONFIG

    id: str
    title: str
    status: ADRStatus = "draft"
    context: str
    decision: str
    consequences: str

    related_requirement_ids: list[str] = Field(default_factory=list)
    related_mind_map_node_ids: list[str] = Field(default_factory=list)

    related_diagram_ids: list[str] = Field(default_factory=list)
    related_waf_evidence_ids: list[str] = Field(default_factory=list)
    missing_evidence_reason: str | None = None

    source_citations: list[dict[str, Any]] = Field(default_factory=list)

    supersedes_adr_id: str | None = None
    created_at: str | None = None

    @field_validator("related_requirement_ids")
    @classmethod
    def _validate_requirement_links(cls, value: list[str]) -> list[str]:
        cleaned = [v.strip() for v in value if v and v.strip()]
        if not cleaned:
            raise ValueError(
                "ADR must link to at least one requirement id (SC-005) via relatedRequirementIds."
            )
        return cleaned

    @field_validator("source_citations")
    @classmethod
    def _validate_source_citations(cls, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not value:
            raise ValueError("ADR must include at least one source citation (SC-011).")
        return value

    @model_validator(mode="after")
    def _validate_evidence_or_reason(self) -> AdrArtifact:
        if not self._has_valid_evidence():
            reason = (self.missing_evidence_reason or "").strip()
            if not reason:
                raise ValueError(
                    "ADR missing evidence (diagram/WAF) and missingEvidenceReason (SC-005)."
                )
            self.missing_evidence_reason = reason
        elif self.missing_evidence_reason is not None:
            self.missing_evidence_reason = self.missing_evidence_reason.strip() or None

        return self

    def _has_valid_evidence(self) -> bool:
        """Check if any diagram or WAF evidence IDs are provided and non-empty."""
        valid_diags = any(v.strip() for v in self.related_diagram_ids if v)
        valid_waf = any(v.strip() for v in self.related_waf_evidence_ids if v)
        return valid_diags or valid_waf


FindingSeverity = Literal["low", "medium", "high", "critical"]


class FindingArtifact(BaseModel):
    """Validation finding artifact (US4)."""

    model_config = _AAA_LAX_CONFIG

    id: str
    title: str
    severity: FindingSeverity
    description: str
    remediation: str

    waf_pillar: str | None = None
    waf_topic: str | None = None

    related_requirement_ids: list[str] = Field(default_factory=list)
    related_diagram_ids: list[str] = Field(default_factory=list)
    related_adr_ids: list[str] = Field(default_factory=list)
    related_mind_map_node_ids: list[str] = Field(default_factory=list)

    source_citations: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str | None = None

    @field_validator("source_citations")
    @classmethod
    def _validate_source_citations(cls, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not value:
            raise ValueError("Finding must include at least one source citation (SC-011).")
        return value


WafCoverageStatus = Literal["covered", "partial", "notCovered"]


class WafEvaluation(BaseModel):
    """Append-only evaluation entry for a WAF checklist item."""

    model_config = _AAA_LAX_CONFIG

    id: str
    status: WafCoverageStatus
    evidence: str
    related_finding_ids: list[str] = Field(default_factory=list)
    source_citations: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str | None = None


class WafChecklistItem(BaseModel):
    """WAF checklist item (stable identity) with append-only evaluations."""

    model_config = _AAA_LAX_CONFIG

    id: str
    pillar: str
    topic: str
    evaluations: list[WafEvaluation] = Field(default_factory=list)


class WafChecklist(BaseModel):
    """Container for WAF checklist metadata and items."""

    model_config = _AAA_LAX_CONFIG

    version: str | None = None
    pillars: list[str] = Field(default_factory=list)
    items: list[WafChecklistItem] = Field(default_factory=list)


IacFormat = Literal["bicep", "terraform", "arm", "yaml", "json", "other"]


class IacFile(BaseModel):
    model_config = _AAA_LAX_CONFIG

    path: str
    format: IacFormat
    content: str


ValidationStatus = Literal["pass", "fail", "skipped"]


class IacValidationResult(BaseModel):
    model_config = _AAA_LAX_CONFIG

    tool: str
    status: ValidationStatus
    output: str | None = None


class IacArtifact(BaseModel):
    """IaC artifact bundle (US5)."""

    model_config = _AAA_LAX_CONFIG

    id: str
    created_at: str | None = None
    files: list[IacFile] = Field(default_factory=list)
    validation_results: list[IacValidationResult] = Field(default_factory=list)


class CostLineItem(BaseModel):
    model_config = _AAA_LAX_CONFIG

    id: str
    name: str
    monthly_quantity: float
    unit_price: float
    monthly_cost: float
    service_name: str | None = None
    product_name: str | None = None
    meter_name: str | None = None
    sku_name: str | None = None
    unit_of_measure: str | None = None


class CostEstimate(BaseModel):
    """Cost estimate artifact (US5)."""

    model_config = _AAA_LAX_CONFIG

    id: str
    created_at: str | None = None
    currency_code: str = "USD"
    total_monthly_cost: float
    line_items: list[CostLineItem] = Field(default_factory=list)
    pricing_gaps: list[dict[str, Any]] = Field(default_factory=list)
    baseline_reference_total_monthly_cost: float | None = None
    variance_pct: float | None = None


class AAAProjectState(BaseModel):
    """Typed overlay of ProjectState.state for AAA.

    The persisted JSON contains many non-AAA keys (e.g., existing context/nfrs).
    This model allows unknown keys to avoid breaking existing state.
    """

    model_config = _AAA_LAX_CONFIG

    # AAA artifacts (defaults applied by `ensure_aaa_defaults`)
    requirements: list[dict[str, Any]] = Field(default_factory=list)
    assumptions: list[dict[str, Any]] = Field(default_factory=list)
    clarification_questions: list[dict[str, Any]] = Field(default_factory=list)
    candidate_architectures: list[dict[str, Any]] = Field(default_factory=list)
    adrs: list[AdrArtifact] = Field(default_factory=list)
    waf_checklist: WafChecklist = Field(default_factory=WafChecklist)
    findings: list[FindingArtifact] = Field(default_factory=list)
    diagrams: list[dict[str, Any]] = Field(default_factory=list)
    iac_artifacts: list[IacArtifact] = Field(default_factory=list)
    cost_estimates: list[CostEstimate] = Field(default_factory=list)
    traceability_links: list[TraceabilityLink] = Field(default_factory=list)

    # US6
    mind_map_coverage: dict[str, Any] = Field(default_factory=dict)
    traceability_issues: list[TraceabilityIssue] = Field(default_factory=list)

    mind_map: dict[str, Any] = Field(default_factory=dict)
    reference_documents: list[ReferenceDocument] = Field(default_factory=list)
    mcp_queries: list[MCPQuery] = Field(default_factory=list)

    ingestion_stats: IngestionStats | None = None
    iteration_events: list[IterationEvent] = Field(default_factory=list)


def ensure_aaa_defaults(state: dict[str, Any]) -> dict[str, Any]:
    """Return a shallow-copied state dict with AAA default keys present."""
    updated = dict(state)

    updated.setdefault("requirements", [])
    updated.setdefault("assumptions", [])
    updated.setdefault("clarificationQuestions", [])
    updated.setdefault("candidateArchitectures", [])
    updated.setdefault("adrs", [])
    waf = updated.get("wafChecklist")
    if not isinstance(waf, dict) or not waf:
        updated["wafChecklist"] = {
            "version": "1",
            "pillars": [
                "reliability",
                "security",
                "cost",
                "operationalExcellence",
                "performanceEfficiency",
            ],
            "items": [],
        }
    else:
        # Ensure minimally expected keys exist for UX + future checklist updates.
        waf.setdefault(
            "pillars",
            [
                "reliability",
                "security",
                "cost",
                "operationalExcellence",
                "performanceEfficiency",
            ],
        )
        waf.setdefault("items", [])
        waf.setdefault("version", "1")
        updated["wafChecklist"] = waf
    updated.setdefault("findings", [])
    updated.setdefault("diagrams", [])
    updated.setdefault("iacArtifacts", [])
    updated.setdefault("costEstimates", [])
    updated.setdefault("traceabilityLinks", [])

    updated.setdefault("mindMapCoverage", {})
    updated.setdefault("traceabilityIssues", [])

    updated.setdefault("mindMap", {})
    updated.setdefault("referenceDocuments", [])
    updated.setdefault("mcpQueries", [])
    updated.setdefault("iterationEvents", [])

    # ingestionStats is optional, but keep key stable if present
    return updated


_TRACEABILITY_NAMESPACE = uuid.UUID("6b9c5af0-22c8-4aa1-a571-3b3f9a4c7d9f")


def stable_traceability_link_id(*, from_type: str, from_id: str, to_type: str, to_id: str) -> str:
    """Create a deterministic id for a link so repeated generation won't duplicate it."""
    key = f"{from_type}:{from_id}->{to_type}:{to_id}"
    return str(uuid.uuid5(_TRACEABILITY_NAMESPACE, key))


def _add_link(
    links: list[dict[str, Any]], from_type: str, from_id: str, to_type: str, to_id: str
) -> None:
    link_id = stable_traceability_link_id(
        from_type=from_type, from_id=from_id, to_type=to_type, to_id=to_id
    )
    links.append(
        {
            "id": link_id,
            "fromType": from_type,
            "fromId": from_id,
            "toType": to_type,
            "toId": to_id,
        }
    )


def _generate_adr_links(links: list[dict[str, Any]], state: dict[str, Any]) -> None:
    for adr in state.get("adrs") or []:
        if not isinstance(adr, dict):
            continue
        adr_id = str(adr.get("id") or "").strip()
        if not adr_id:
            continue

        _link_adr_to_requirements(links, adr_id, adr)
        _link_adr_to_nodes(links, adr_id, adr)
        _link_adr_to_diagrams(links, adr_id, adr)
        _link_adr_to_waf(links, adr_id, adr)


def _link_adr_to_requirements(links: list[dict[str, Any]], aid: str, adr: dict[str, Any]) -> None:
    for req_id in adr.get("relatedRequirementIds") or []:
        rid = str(req_id or "").strip()
        if rid:
            _add_link(links, "adr", aid, "requirement", rid)


def _link_adr_to_nodes(links: list[dict[str, Any]], aid: str, adr: dict[str, Any]) -> None:
    for node_id in adr.get("relatedMindMapNodeIds") or []:
        nid = str(node_id or "").strip()
        if nid:
            _add_link(links, "adr", aid, "mindMapNode", nid)


def _link_adr_to_diagrams(links: list[dict[str, Any]], aid: str, adr: dict[str, Any]) -> None:
    for diagram_id in adr.get("relatedDiagramIds") or []:
        did = str(diagram_id or "").strip()
        if did:
            _add_link(links, "adr", aid, "diagram", did)


def _link_adr_to_waf(links: list[dict[str, Any]], aid: str, adr: dict[str, Any]) -> None:
    for waf_id in adr.get("relatedWafEvidenceIds") or []:
        wid = str(waf_id or "").strip()
        if wid:
            _add_link(links, "adr", aid, "wafEvidence", wid)


def _generate_finding_links(links: list[dict[str, Any]], state: dict[str, Any]) -> None:
    for finding in state.get("findings") or []:
        if not isinstance(finding, dict):
            continue
        fid = str(finding.get("id") or "").strip()
        if not fid:
            continue

        _link_finding_to_requirements(links, fid, finding)
        _link_finding_to_nodes(links, fid, finding)
        _link_finding_to_diagrams(links, fid, finding)
        _link_finding_to_adrs(links, fid, finding)


def _link_finding_to_requirements(
    links: list[dict[str, Any]], fid: str, f: dict[str, Any]
) -> None:
    for req_id in f.get("relatedRequirementIds") or []:
        rid = str(req_id or "").strip()
        if rid:
            _add_link(links, "finding", fid, "requirement", rid)


def _link_finding_to_nodes(links: list[dict[str, Any]], fid: str, f: dict[str, Any]) -> None:
    for node_id in f.get("relatedMindMapNodeIds") or []:
        nid = str(node_id or "").strip()
        if nid:
            _add_link(links, "finding", fid, "mindMapNode", nid)


def _link_finding_to_diagrams(links: list[dict[str, Any]], fid: str, f: dict[str, Any]) -> None:
    for diagram_id in f.get("relatedDiagramIds") or []:
        did = str(diagram_id or "").strip()
        if did:
            _add_link(links, "finding", fid, "diagram", did)


def _link_finding_to_adrs(links: list[dict[str, Any]], fid: str, f: dict[str, Any]) -> None:
    for adr_id in f.get("relatedAdrIds") or []:
        aid = str(adr_id or "").strip()
        if aid:
            _add_link(links, "finding", fid, "adr", aid)


def generate_traceability_links(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Best-effort link generation from known artifacts."""
    links: list[dict[str, Any]] = []
    _generate_adr_links(links, state)
    _generate_finding_links(links, state)
    return links


def _check_link_fields(link: dict[str, Any]) -> str | None:
    """Return error message if required traceability fields are missing."""
    required_fields = ["fromType", "fromId", "toType", "toId"]
    missing = [f for f in required_fields if not str(link.get(f) or "").strip()]
    if missing:
        return f"Traceability link missing fields: {', '.join(missing)}"
    return None


def verify_traceability_links(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Return a list of non-blocking issues about traceability links."""
    issues: list[dict[str, Any]] = []
    seen: set[str] = set()

    links = state.get("traceabilityLinks")
    if not isinstance(links, list):
        return issues

    for link in links:
        if not isinstance(link, dict):
            continue
        link_id = str(link.get("id") or "").strip()
        if not link_id:
            continue

        if link_id in seen:
            issues.append(
                {
                    "id": stable_traceability_link_id(
                        from_type="issue",
                        from_id=link_id,
                        to_type="duplicate",
                        to_id="id",
                    ),
                    "kind": "duplicate_link_id",
                    "message": "Duplicate traceability link id detected",
                    "linkId": link_id,
                }
            )
        seen.add(link_id)

        error_msg = _check_link_fields(link)
        if error_msg:
            issues.append(
                {
                    "id": stable_traceability_link_id(
                        from_type="issue",
                        from_id=link_id,
                        to_type="missing",
                        to_id="fields",
                    ),
                    "kind": "invalid_link",
                    "message": error_msg,
                    "linkId": link_id,
                }
            )

    return issues


def _enrich_links(updated: dict[str, Any], existing_ids: set[str]) -> None:
    """Helper to append new traceability links to state."""
    links_list = updated.get("traceabilityLinks")
    if not isinstance(links_list, list):
        return

    for link in generate_traceability_links(updated):
        if link["id"] not in existing_ids:
            links_list.append(link)
            existing_ids.add(link["id"])


def _enrich_issues(updated: dict[str, Any], existing_ids: set[str]) -> None:
    """Helper to append new traceability issues to state."""
    issues_list = updated.get("traceabilityIssues")
    if not isinstance(issues_list, list):
        return

    for issue in verify_traceability_links(updated):
        if issue["id"] not in existing_ids:
            issues_list.append(issue)
            existing_ids.add(issue["id"])


def apply_us6_enrichment(state: dict[str, Any]) -> dict[str, Any]:
    """Apply US6 enrichment (traceability generation/verification)."""
    updated = dict(state)
    updated.setdefault("traceabilityLinks", [])
    updated.setdefault("traceabilityIssues", [])

    existing_links = updated["traceabilityLinks"]
    if not isinstance(existing_links, list):
        existing_links = []
        updated["traceabilityLinks"] = existing_links

    existing_ids = {
        str(i.get("id")) for i in existing_links if isinstance(i, dict) and i.get("id")
    }
    _enrich_links(updated, existing_ids)

    existing_issues = updated["traceabilityIssues"]
    if not isinstance(existing_issues, list):
        existing_issues = []
        updated["traceabilityIssues"] = existing_issues

    existing_issue_ids = {
        str(i.get("id")) for i in existing_issues if isinstance(i, dict) and i.get("id")
    }
    _enrich_issues(updated, existing_issue_ids)

    return updated

