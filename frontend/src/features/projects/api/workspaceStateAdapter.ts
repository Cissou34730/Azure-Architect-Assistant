import type {
  ProjectState,
  ProjectStateTechnicalConstraints,
} from "../types/api-project";
import type { ProjectWorkspaceView } from "../types/api-workspace";

function getTechnicalConstraints(
  technicalConstraints: ProjectWorkspaceView["inputs"]["technicalConstraints"],
): ProjectStateTechnicalConstraints {
  return technicalConstraints ?? { constraints: [], assumptions: [] };
}

function getBaseState(workspace: ProjectWorkspaceView): Omit<ProjectState, "technicalConstraints"> {
  const { context } = workspace.inputs;

  return {
    projectId: workspace.project.id,
    context,
    nfrs: workspace.inputs.nfrs ?? undefined,
    applicationStructure: workspace.inputs.applicationStructure ?? undefined,
    dataCompliance: workspace.inputs.dataCompliance ?? undefined,
    openQuestions: workspace.inputs.openQuestions,
    lastUpdated: workspace.state.lastUpdated ?? "",
    requirements: workspace.artifacts.requirements,
    assumptions: workspace.artifacts.assumptions,
    clarificationQuestions: workspace.artifacts.clarificationQuestions,
    candidateArchitectures: workspace.artifacts.candidateArchitectures,
    adrs: workspace.artifacts.adrs,
    findings: workspace.artifacts.findings,
    diagrams: workspace.artifacts.diagrams,
    iacArtifacts: workspace.artifacts.iacArtifacts,
    costEstimates: workspace.artifacts.costEstimates,
    traceabilityLinks: workspace.artifacts.traceabilityLinks,
    mindMapCoverage: workspace.artifacts.mindMapCoverage ?? { topics: {} },
    traceabilityIssues: workspace.artifacts.traceabilityIssues,
    mindMap: workspace.artifacts.mindMap ?? {},
    referenceDocuments: workspace.documents.items,
    mcpQueries: workspace.artifacts.mcpQueries,
    wafChecklist: workspace.artifacts.wafChecklist ?? undefined,
    projectDocumentStats: workspace.documents.stats ?? undefined,
    analysisSummary: workspace.artifacts.analysisSummary ?? undefined,
    iterationEvents: workspace.artifacts.iterationEvents,
    summary: context.summary,
    objectives: context.objectives,
    targetUsers: context.targetUsers,
    scenarioType: context.scenarioType,
  };
}

export function workspaceToProjectState(workspace: ProjectWorkspaceView): ProjectState {
  return {
    ...getBaseState(workspace),
    technicalConstraints: getTechnicalConstraints(workspace.inputs.technicalConstraints),
  };
}