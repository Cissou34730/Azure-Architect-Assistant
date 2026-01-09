"""Pydantic models for AAA artifacts stored inside ProjectState.state.

Phase 2 scope (T007): define minimal typed shapes for AAA state. These models
are used at service boundaries to validate and normalize state reads/writes.

Important: the wider application already stores additional keys in ProjectState;
models in this module must allow unknown fields.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Set, Tuple
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SourceCitationKind(str, Enum):
    reference_document = "referenceDocument"
    mcp = "mcp"


class SourceCitation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    kind: SourceCitationKind
    referenceDocumentId: Optional[str] = None
    mcpQueryId: Optional[str] = None
    url: Optional[str] = None
    note: Optional[str] = None


class ReferenceDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    category: str
    title: str
    url: Optional[str] = None
    accessedAt: str


class MCPQueryPhase(str, Enum):
    architecture = "architecture"
    validation = "validation"
    iac = "iac"
    other = "other"


class MCPQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    queryText: str
    phase: MCPQueryPhase
    resultUrls: List[str] = Field(default_factory=list)
    selectedSnippets: Optional[List[str]] = None
    executedAt: str


class IngestionFailure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    documentId: Optional[str] = None
    fileName: str
    reason: str


class IngestionStats(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attemptedDocuments: int = 0
    parsedDocuments: int = 0
    failedDocuments: int = 0
    failures: List[IngestionFailure] = Field(default_factory=list)


class IterationEventKind(str, Enum):
    propose = "propose"
    challenge = "challenge"


class IterationEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    kind: IterationEventKind
    text: str
    citations: List[SourceCitation] = Field(default_factory=list)
    architectResponseMessageId: Optional[str] = None
    createdAt: str
    relatedArtifactIds: List[str] = Field(default_factory=list)


class TraceabilityLink(BaseModel):
    """A directional trace link between artifacts (for explainability/audit)."""

    model_config = ConfigDict(extra="allow")

    id: str
    fromType: str
    fromId: str
    toType: str
    toId: str


class TraceabilityIssue(BaseModel):
    """Non-blocking traceability verification issue (US6)."""

    model_config = ConfigDict(extra="allow")

    id: str
    kind: str
    message: str
    linkId: Optional[str] = None
    createdAt: Optional[str] = None


ADRStatus = Literal["draft", "accepted", "rejected", "superseded"]


class AdrArtifact(BaseModel):
    """Decision record artifact (US3)."""

    model_config = ConfigDict(extra="allow")

    id: str
    title: str
    status: ADRStatus = "draft"
    context: str
    decision: str
    consequences: str

    relatedRequirementIds: List[str] = Field(default_factory=list)
    relatedMindMapNodeIds: List[str] = Field(default_factory=list)

    relatedDiagramIds: List[str] = Field(default_factory=list)
    relatedWafEvidenceIds: List[str] = Field(default_factory=list)
    missingEvidenceReason: Optional[str] = None

    sourceCitations: List[Dict[str, Any]] = Field(default_factory=list)

    supersedesAdrId: Optional[str] = None
    createdAt: Optional[str] = None

    @field_validator("relatedRequirementIds")
    @classmethod
    def _validate_requirement_links(cls, value: List[str]) -> List[str]:
        cleaned = [v.strip() for v in value if v and v.strip()]
        if not cleaned:
            raise ValueError(
                "ADR must link to at least one requirement id (SC-005) via relatedRequirementIds."
            )
        return cleaned

    @field_validator("sourceCitations")
    @classmethod
    def _validate_source_citations(cls, value: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not value:
            raise ValueError("ADR must include at least one source citation (SC-011).")
        return value

    @model_validator(mode="after")
    def _validate_evidence_or_reason(self) -> "AdrArtifact":
        has_diagram = bool([v for v in self.relatedDiagramIds if (v or "").strip()])
        has_waf = bool([v for v in self.relatedWafEvidenceIds if (v or "").strip()])
        if not has_diagram and not has_waf:
            reason = (self.missingEvidenceReason or "").strip()
            if not reason:
                raise ValueError(
                    "ADR must include relatedDiagramIds or relatedWafEvidenceIds, or provide missingEvidenceReason (SC-005)."
                )
            self.missingEvidenceReason = reason
        else:
            if self.missingEvidenceReason is not None:
                stripped = self.missingEvidenceReason.strip()
                self.missingEvidenceReason = stripped or None
        return self


FindingSeverity = Literal["low", "medium", "high", "critical"]


class FindingArtifact(BaseModel):
    """Validation finding artifact (US4)."""

    model_config = ConfigDict(extra="allow")

    id: str
    title: str
    severity: FindingSeverity
    description: str
    remediation: str

    wafPillar: Optional[str] = None
    wafTopic: Optional[str] = None

    relatedRequirementIds: List[str] = Field(default_factory=list)
    relatedDiagramIds: List[str] = Field(default_factory=list)
    relatedAdrIds: List[str] = Field(default_factory=list)
    relatedMindMapNodeIds: List[str] = Field(default_factory=list)

    sourceCitations: List[Dict[str, Any]] = Field(default_factory=list)
    createdAt: Optional[str] = None

    @field_validator("sourceCitations")
    @classmethod
    def _validate_source_citations(cls, value: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not value:
            raise ValueError("Finding must include at least one source citation (SC-011).")
        return value


WafCoverageStatus = Literal["covered", "partial", "notCovered"]


class WafEvaluation(BaseModel):
    """Append-only evaluation entry for a WAF checklist item."""

    model_config = ConfigDict(extra="allow")

    id: str
    status: WafCoverageStatus
    evidence: str
    relatedFindingIds: List[str] = Field(default_factory=list)
    sourceCitations: List[Dict[str, Any]] = Field(default_factory=list)
    createdAt: Optional[str] = None


class WafChecklistItem(BaseModel):
    """WAF checklist item (stable identity) with append-only evaluations."""

    model_config = ConfigDict(extra="allow")

    id: str
    pillar: str
    topic: str
    evaluations: List[WafEvaluation] = Field(default_factory=list)


class WafChecklist(BaseModel):
    """Container for WAF checklist metadata and items."""

    model_config = ConfigDict(extra="allow")

    version: Optional[str] = None
    pillars: List[str] = Field(default_factory=list)
    items: List[WafChecklistItem] = Field(default_factory=list)


IacFormat = Literal["bicep", "terraform", "arm", "yaml", "json", "other"]


class IacFile(BaseModel):
    model_config = ConfigDict(extra="allow")

    path: str
    format: IacFormat
    content: str


ValidationStatus = Literal["pass", "fail", "skipped"]


class IacValidationResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    tool: str
    status: ValidationStatus
    output: Optional[str] = None


class IacArtifact(BaseModel):
    """IaC artifact bundle (US5)."""

    model_config = ConfigDict(extra="allow")

    id: str
    createdAt: Optional[str] = None
    files: List[IacFile] = Field(default_factory=list)
    validationResults: List[IacValidationResult] = Field(default_factory=list)


class CostLineItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    monthlyQuantity: float
    unitPrice: float
    monthlyCost: float
    serviceName: Optional[str] = None
    productName: Optional[str] = None
    meterName: Optional[str] = None
    skuName: Optional[str] = None
    unitOfMeasure: Optional[str] = None


class CostEstimate(BaseModel):
    """Cost estimate artifact (US5)."""

    model_config = ConfigDict(extra="allow")

    id: str
    createdAt: Optional[str] = None
    currencyCode: str = "USD"
    totalMonthlyCost: float
    lineItems: List[CostLineItem] = Field(default_factory=list)
    pricingGaps: List[Dict[str, Any]] = Field(default_factory=list)
    baselineReferenceTotalMonthlyCost: Optional[float] = None
    variancePct: Optional[float] = None


class AAAProjectState(BaseModel):
    """Typed overlay of ProjectState.state for AAA.

    The persisted JSON contains many non-AAA keys (e.g., existing context/nfrs).
    This model allows unknown keys to avoid breaking existing state.
    """

    model_config = ConfigDict(extra="allow")

    # AAA artifacts (defaults applied by `ensure_aaa_defaults`)
    requirements: List[Dict[str, Any]] = Field(default_factory=list)
    assumptions: List[Dict[str, Any]] = Field(default_factory=list)
    clarificationQuestions: List[Dict[str, Any]] = Field(default_factory=list)
    candidateArchitectures: List[Dict[str, Any]] = Field(default_factory=list)
    adrs: List[AdrArtifact] = Field(default_factory=list)
    wafChecklist: WafChecklist = Field(default_factory=WafChecklist)
    findings: List[FindingArtifact] = Field(default_factory=list)
    diagrams: List[Dict[str, Any]] = Field(default_factory=list)
    iacArtifacts: List[IacArtifact] = Field(default_factory=list)
    costEstimates: List[CostEstimate] = Field(default_factory=list)
    traceabilityLinks: List[TraceabilityLink] = Field(default_factory=list)

    # US6
    mindMapCoverage: Dict[str, Any] = Field(default_factory=dict)
    traceabilityIssues: List[TraceabilityIssue] = Field(default_factory=list)

    mindMap: Dict[str, Any] = Field(default_factory=dict)
    referenceDocuments: List[ReferenceDocument] = Field(default_factory=list)
    mcpQueries: List[MCPQuery] = Field(default_factory=list)

    ingestionStats: Optional[IngestionStats] = None
    iterationEvents: List[IterationEvent] = Field(default_factory=list)


def ensure_aaa_defaults(state: Dict[str, Any]) -> Dict[str, Any]:
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


def generate_traceability_links(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Best-effort link generation from known artifacts.

    This is intentionally conservative and focuses on artifacts that already
    carry explicit relationship fields.
    """

    links: List[Dict[str, Any]] = []

    def _add(from_type: str, from_id: str, to_type: str, to_id: str) -> None:
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

    for adr in state.get("adrs") or []:
        if not isinstance(adr, dict):
            continue
        adr_id = str(adr.get("id") or "").strip()
        if not adr_id:
            continue
        for req_id in adr.get("relatedRequirementIds") or []:
            rid = str(req_id or "").strip()
            if rid:
                _add("adr", adr_id, "requirement", rid)
        for node_id in adr.get("relatedMindMapNodeIds") or []:
            nid = str(node_id or "").strip()
            if nid:
                _add("adr", adr_id, "mindMapNode", nid)
        for diagram_id in adr.get("relatedDiagramIds") or []:
            did = str(diagram_id or "").strip()
            if did:
                _add("adr", adr_id, "diagram", did)
        for waf_id in adr.get("relatedWafEvidenceIds") or []:
            wid = str(waf_id or "").strip()
            if wid:
                _add("adr", adr_id, "wafEvidence", wid)

    for finding in state.get("findings") or []:
        if not isinstance(finding, dict):
            continue
        fid = str(finding.get("id") or "").strip()
        if not fid:
            continue
        for req_id in finding.get("relatedRequirementIds") or []:
            rid = str(req_id or "").strip()
            if rid:
                _add("finding", fid, "requirement", rid)
        for node_id in finding.get("relatedMindMapNodeIds") or []:
            nid = str(node_id or "").strip()
            if nid:
                _add("finding", fid, "mindMapNode", nid)
        for diagram_id in finding.get("relatedDiagramIds") or []:
            did = str(diagram_id or "").strip()
            if did:
                _add("finding", fid, "diagram", did)
        for adr_id in finding.get("relatedAdrIds") or []:
            aid = str(adr_id or "").strip()
            if aid:
                _add("finding", fid, "adr", aid)

    return links


def verify_traceability_links(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return a list of non-blocking issues about traceability links."""
    issues: List[Dict[str, Any]] = []
    seen: Set[str] = set()

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
                        from_type="issue", from_id=link_id, to_type="duplicate", to_id="id"
                    ),
                    "kind": "duplicate_link_id",
                    "message": "Duplicate traceability link id detected",
                    "linkId": link_id,
                }
            )
        seen.add(link_id)

        required_fields = ["fromType", "fromId", "toType", "toId"]
        missing = [f for f in required_fields if not str(link.get(f) or "").strip()]
        if missing:
            issues.append(
                {
                    "id": stable_traceability_link_id(
                        from_type="issue", from_id=link_id, to_type="missing", to_id="fields"
                    ),
                    "kind": "invalid_link",
                    "message": f"Traceability link missing fields: {', '.join(missing)}",
                    "linkId": link_id,
                }
            )

    return issues


def apply_us6_enrichment(state: Dict[str, Any]) -> Dict[str, Any]:
    """Apply US6 enrichment (traceability generation/verification).

    - Appends deterministic traceability links derived from artifacts.
    - Appends non-blocking traceability issues.
    """
    updated = dict(state)
    updated.setdefault("traceabilityLinks", [])
    updated.setdefault("traceabilityIssues", [])

    existing_links = updated.get("traceabilityLinks")
    if not isinstance(existing_links, list):
        existing_links = []
        updated["traceabilityLinks"] = existing_links

    existing_ids: Set[str] = set()
    for l in existing_links:
        if isinstance(l, dict) and str(l.get("id") or "").strip():
            existing_ids.add(str(l["id"]))

    for link in generate_traceability_links(updated):
        if link["id"] not in existing_ids:
            existing_links.append(link)
            existing_ids.add(link["id"])

    issues_list = updated.get("traceabilityIssues")
    if not isinstance(issues_list, list):
        issues_list = []
        updated["traceabilityIssues"] = issues_list

    existing_issue_ids: Set[str] = set(
        str(i.get("id")) for i in issues_list if isinstance(i, dict) and i.get("id")
    )
    for issue in verify_traceability_links(updated):
        if issue["id"] not in existing_issue_ids:
            issues_list.append(issue)
            existing_issue_ids.add(issue["id"])

    return updated
