import { AdrLibrary, CostBreakdown, IacViewer } from "../../projects/components/deliverables";
import { AssumptionsTab } from "../../projects/components/unified/LeftContextPanel/AssumptionsTab";
import { QuestionsTab } from "../../projects/components/unified/LeftContextPanel/QuestionsTab";
import { RequirementsTab } from "../../projects/components/unified/LeftContextPanel/RequirementsTab";
import {
  CandidateArchitectureView,
  FindingsList,
  IterationEventsView,
  McpQueriesView,
  TraceabilityView,
} from "../../projects/components/unified/workspace/ArtifactViewRenderers";
import type { ProjectWorkspaceStaticTabRenderer } from "../../projects/workspaceTabRenderTypes";

export const projectWorkspaceAgentRenderers = {
  ["artifact-requirements"]: ({ projectState }) => <RequirementsTab requirements={projectState.requirements} />,
  ["artifact-assumptions"]: ({ projectState }) => <AssumptionsTab assumptions={projectState.assumptions} />,
  ["artifact-questions"]: ({ projectState }) => <QuestionsTab questions={projectState.clarificationQuestions} />,
  ["artifact-adrs"]: ({ projectState }) => <AdrLibrary adrs={projectState.adrs} />,
  ["artifact-findings"]: ({ projectState, hasArtifacts }) => <FindingsList projectState={projectState} hasArtifacts={hasArtifacts} />,
  ["artifact-iac"]: ({ projectState }) => <IacViewer iacArtifacts={projectState.iacArtifacts} />,
  ["artifact-costs"]: ({ projectState }) => <CostBreakdown costEstimates={projectState.costEstimates} />,
  ["artifact-traceability"]: ({ projectState }) => <TraceabilityView projectState={projectState} />,
  ["artifact-candidates"]: ({ projectState }) => <CandidateArchitectureView projectState={projectState} />,
  ["artifact-iterations"]: ({ projectState }) => <IterationEventsView projectState={projectState} />,
  ["artifact-mcp"]: ({ projectState }) => <McpQueriesView projectState={projectState} />,
} satisfies Partial<Record<string, ProjectWorkspaceStaticTabRenderer>>;