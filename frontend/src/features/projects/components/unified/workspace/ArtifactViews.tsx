import { type ReactElement } from "react";
import type { ProjectState } from "../../../../../types/api";
import { RequirementsTab } from "../LeftContextPanel/RequirementsTab";
import { AssumptionsTab } from "../LeftContextPanel/AssumptionsTab";
import { QuestionsTab } from "../LeftContextPanel/QuestionsTab";
import { AdrLibrary, DiagramGallery, IacViewer, CostBreakdown } from "../../deliverables";
import type { ArtifactTab } from "./types";
import { WafChecklistView } from "./WafChecklistView";
import {
  FindingsList,
  TraceabilityView,
  CandidateArchitectureView,
  IterationEventsView,
  McpQueriesView,
} from "./ArtifactViewRenderers";

interface ArtifactViewProps {
  readonly tabKind: ArtifactTab;
  readonly projectState: ProjectState;
  readonly hasArtifacts: boolean;
}

type ArtifactRenderer = (props: ArtifactViewProps) => ReactElement;

const artifactRenderers: Record<ArtifactTab, ArtifactRenderer> = {
  ["artifact-requirements"]: ({ projectState }) => (
    <RequirementsTab requirements={projectState.requirements} />
  ),
  ["artifact-assumptions"]: ({ projectState }) => (
    <AssumptionsTab assumptions={projectState.assumptions} />
  ),
  ["artifact-questions"]: ({ projectState }) => (
    <QuestionsTab questions={projectState.clarificationQuestions} />
  ),
  ["artifact-adrs"]: ({ projectState }) => <AdrLibrary adrs={projectState.adrs} />,
  ["artifact-diagrams"]: ({ projectState }) => (
    <DiagramGallery diagrams={projectState.diagrams} />
  ),
  ["artifact-iac"]: ({ projectState }) => (
    <IacViewer iacArtifacts={projectState.iacArtifacts} />
  ),
  ["artifact-costs"]: ({ projectState }) => (
    <CostBreakdown costEstimates={projectState.costEstimates} />
  ),
  ["artifact-findings"]: ({ projectState, hasArtifacts }) => (
    <FindingsList
      projectState={projectState}
      hasArtifacts={hasArtifacts}
    />
  ),
  ["artifact-waf"]: ({ projectState }) => <WafChecklistView projectState={projectState} />,
  ["artifact-traceability"]: ({ projectState }) => (
    <TraceabilityView projectState={projectState} />
  ),
  ["artifact-candidates"]: ({ projectState }) => (
    <CandidateArchitectureView projectState={projectState} />
  ),
  ["artifact-iterations"]: ({ projectState }) => (
    <IterationEventsView projectState={projectState} />
  ),
  ["artifact-mcp"]: ({ projectState }) => (
    <McpQueriesView projectState={projectState} />
  ),
};

export function ArtifactViews(props: ArtifactViewProps) {
  return artifactRenderers[props.tabKind](props);
}



