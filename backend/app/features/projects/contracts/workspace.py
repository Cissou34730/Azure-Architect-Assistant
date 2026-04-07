"""Projects feature contracts for composed workspace responses."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.features.agent.contracts import ConversationSummaryContract
from app.features.checklists.contracts import ChecklistSummaryContract
from app.features.diagrams.contracts import DiagramSummaryContract
from app.features.knowledge.contracts import KnowledgeBaseSummaryContract
from app.features.settings.contracts import RuntimeSelectionContract


class _WorkspaceModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class ProjectWorkspaceProjectSummary(_WorkspaceModel):
    id: str
    name: str
    created_at: str = Field(alias="createdAt")
    text_requirements: str = Field(alias="textRequirements")
    document_count: int = Field(alias="documentCount")


class ProjectWorkspaceStateSummary(_WorkspaceModel):
    last_updated: str | None = Field(default=None, alias="lastUpdated")
    artifact_keys: list[str] = Field(default_factory=list, alias="artifactKeys")


class ProjectWorkspaceInputs(_WorkspaceModel):
    context: dict[str, Any] = Field(default_factory=dict)
    nfrs: dict[str, Any] | None = None
    application_structure: dict[str, Any] | None = Field(default=None, alias="applicationStructure")
    data_compliance: dict[str, Any] | None = Field(default=None, alias="dataCompliance")
    technical_constraints: dict[str, Any] | None = Field(default=None, alias="technicalConstraints")
    open_questions: list[Any] = Field(default_factory=list, alias="openQuestions")


class ProjectWorkspaceDocuments(_WorkspaceModel):
    items: list[dict[str, Any]] = Field(default_factory=list)
    stats: dict[str, Any] | None = None


class ProjectWorkspaceArtifacts(_WorkspaceModel):
    requirements: list[dict[str, Any]] = Field(default_factory=list)
    assumptions: list[dict[str, Any]] = Field(default_factory=list)
    clarification_questions: list[dict[str, Any]] = Field(default_factory=list, alias="clarificationQuestions")
    candidate_architectures: list[dict[str, Any]] = Field(default_factory=list, alias="candidateArchitectures")
    adrs: list[dict[str, Any]] = Field(default_factory=list)
    findings: list[dict[str, Any]] = Field(default_factory=list)
    diagrams: list[dict[str, Any]] = Field(default_factory=list)
    iac_artifacts: list[dict[str, Any]] = Field(default_factory=list, alias="iacArtifacts")
    cost_estimates: list[dict[str, Any]] = Field(default_factory=list, alias="costEstimates")
    traceability_links: list[dict[str, Any]] = Field(default_factory=list, alias="traceabilityLinks")
    traceability_issues: list[dict[str, Any]] = Field(default_factory=list, alias="traceabilityIssues")
    mind_map_coverage: dict[str, Any] | None = Field(default=None, alias="mindMapCoverage")
    mind_map: dict[str, Any] | None = Field(default=None, alias="mindMap")
    mcp_queries: list[dict[str, Any]] = Field(default_factory=list, alias="mcpQueries")
    iteration_events: list[dict[str, Any]] = Field(default_factory=list, alias="iterationEvents")
    analysis_summary: dict[str, Any] | None = Field(default=None, alias="analysisSummary")
    waf_checklist: dict[str, Any] | None = Field(default=None, alias="wafChecklist")


AgentWorkspaceSummary = ConversationSummaryContract
ProjectWorkspaceChecklistSummary = ChecklistSummaryContract
ProjectWorkspaceKnowledgeBaseSummary = KnowledgeBaseSummaryContract
ProjectWorkspaceDiagramSummary = DiagramSummaryContract
ProjectWorkspaceSettingsSummary = RuntimeSelectionContract


class ProjectWorkspaceView(_WorkspaceModel):
    project: ProjectWorkspaceProjectSummary
    state: ProjectWorkspaceStateSummary
    inputs: ProjectWorkspaceInputs = Field(default_factory=ProjectWorkspaceInputs)
    documents: ProjectWorkspaceDocuments = Field(default_factory=ProjectWorkspaceDocuments)
    artifacts: ProjectWorkspaceArtifacts = Field(default_factory=ProjectWorkspaceArtifacts)
    agent: AgentWorkspaceSummary
    checklists: list[ProjectWorkspaceChecklistSummary] = Field(default_factory=list)
    knowledge_bases: list[ProjectWorkspaceKnowledgeBaseSummary] = Field(
        default_factory=list,
        alias="knowledgeBases",
    )
    diagrams: list[ProjectWorkspaceDiagramSummary] = Field(default_factory=list)
    settings: ProjectWorkspaceSettingsSummary


def workspace_view_to_project_state(workspace: ProjectWorkspaceView) -> dict[str, Any]:
    state: dict[str, Any] = {
        "projectId": workspace.project.id,
        "lastUpdated": workspace.state.last_updated,
        "context": workspace.inputs.context,
        "openQuestions": workspace.inputs.open_questions,
        "requirements": workspace.artifacts.requirements,
        "assumptions": workspace.artifacts.assumptions,
        "clarificationQuestions": workspace.artifacts.clarification_questions,
        "candidateArchitectures": workspace.artifacts.candidate_architectures,
        "adrs": workspace.artifacts.adrs,
        "findings": workspace.artifacts.findings,
        "diagrams": workspace.artifacts.diagrams,
        "iacArtifacts": workspace.artifacts.iac_artifacts,
        "costEstimates": workspace.artifacts.cost_estimates,
        "traceabilityLinks": workspace.artifacts.traceability_links,
        "traceabilityIssues": workspace.artifacts.traceability_issues,
        "mindMapCoverage": workspace.artifacts.mind_map_coverage,
        "mindMap": workspace.artifacts.mind_map,
        "referenceDocuments": workspace.documents.items,
        "projectDocumentStats": workspace.documents.stats,
        "analysisSummary": workspace.artifacts.analysis_summary,
        "mcpQueries": workspace.artifacts.mcp_queries,
        "iterationEvents": workspace.artifacts.iteration_events,
        "wafChecklist": workspace.artifacts.waf_checklist,
    }
    if workspace.inputs.nfrs is not None:
        state["nfrs"] = workspace.inputs.nfrs
    if workspace.inputs.application_structure is not None:
        state["applicationStructure"] = workspace.inputs.application_structure
    if workspace.inputs.data_compliance is not None:
        state["dataCompliance"] = workspace.inputs.data_compliance
    if workspace.inputs.technical_constraints is not None:
        state["technicalConstraints"] = workspace.inputs.technical_constraints
    if workspace.documents.stats is not None:
        state["ingestionStats"] = workspace.documents.stats

    context = workspace.inputs.context
    if "summary" in context:
        state["summary"] = context.get("summary")
    if "objectives" in context:
        state["objectives"] = context.get("objectives")
    if "targetUsers" in context:
        state["targetUsers"] = context.get("targetUsers")
    if "scenarioType" in context:
        state["scenarioType"] = context.get("scenarioType")

    return state
