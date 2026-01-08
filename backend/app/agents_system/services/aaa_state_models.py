"""Pydantic models for AAA artifacts stored inside ProjectState.state.

Phase 2 scope (T007): define minimal typed shapes for AAA state. These models
are used at service boundaries to validate and normalize state reads/writes.

Important: the wider application already stores additional keys in ProjectState;
models in this module must allow unknown fields.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


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
    adrs: List[Dict[str, Any]] = Field(default_factory=list)
    wafChecklist: Dict[str, Any] = Field(default_factory=dict)
    findings: List[Dict[str, Any]] = Field(default_factory=list)
    diagrams: List[Dict[str, Any]] = Field(default_factory=list)
    iacArtifacts: List[Dict[str, Any]] = Field(default_factory=list)
    costEstimates: List[Dict[str, Any]] = Field(default_factory=list)
    traceabilityLinks: List[Dict[str, Any]] = Field(default_factory=list)

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

    updated.setdefault("mindMap", {})
    updated.setdefault("referenceDocuments", [])
    updated.setdefault("mcpQueries", [])
    updated.setdefault("iterationEvents", [])

    # ingestionStats is optional, but keep key stable if present
    return updated
