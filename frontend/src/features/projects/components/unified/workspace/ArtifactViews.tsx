import { type ReactElement } from "react";
import {
  MessageSquareQuote,
  ShieldAlert,
  FileSearch,
  Layers,
  Waypoints,
} from "lucide-react";
import type { ProjectState } from "../../../../../types/api";
import { RequirementsTab } from "../LeftContextPanel/RequirementsTab";
import { AssumptionsTab } from "../LeftContextPanel/AssumptionsTab";
import { QuestionsTab } from "../LeftContextPanel/QuestionsTab";
import { AdrLibrary, DiagramGallery, IacViewer, CostBreakdown } from "../../deliverables";
import { EmptyArtifactState } from "./EmptyArtifactState";
import type { ArtifactTab } from "./types";
import { WafChecklistView } from "./WafChecklistView";

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

interface FindingsListProps {
  readonly projectState: ProjectState;
  readonly hasArtifacts: boolean;
}

function FindingsList({
  projectState,
  hasArtifacts,
}: FindingsListProps) {
  const findings = safeArray(projectState.findings);
  if (!hasArtifacts) {
    return (
      <EmptyArtifactState
        icon={ShieldAlert}
        title="No findings yet"
        description="Findings will appear after you run analysis from Inputs setup."
      />
    );
  }
  if (findings.length === 0) {
    return (
      <div className="p-6 text-sm text-dim">
        No findings available for this project.
      </div>
    );
  }
  return (
    <div className="p-6 space-y-4">
      {findings.map((finding) => (
        <div key={finding.id} className="rounded-lg border border-border bg-card p-4">
          <div className="flex items-start gap-3">
            <div className="h-8 w-8 rounded-md bg-warning-soft flex items-center justify-center">
              <ShieldAlert className="h-4 w-4 text-warning" />
            </div>
            <div>
              <div className="text-sm font-semibold text-foreground">{finding.title}</div>
              <div className="text-xs text-dim">{finding.description}</div>
              <div className="mt-2 text-xs text-secondary">{finding.remediation}</div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function safeArray<T>(value: readonly T[] | undefined): readonly T[] {
  if (value === undefined) {
    return [];
  }
  return value;
}

function TraceabilityView({ projectState }: { readonly projectState: ProjectState }) {
  const linkCount = safeArray(projectState.traceabilityLinks).length;
  const issueCount = safeArray(projectState.traceabilityIssues).length;
  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center gap-3">
        <div className="h-9 w-9 rounded-lg bg-info-soft flex items-center justify-center">
          <Waypoints className="h-4 w-4 text-info" />
        </div>
        <div>
          <p className="text-sm font-semibold text-foreground">Traceability</p>
          <p className="text-xs text-dim">
            {linkCount} links, {issueCount} issues
          </p>
        </div>
      </div>
    </div>
  );
}

function CandidateArchitectureView({ projectState }: { readonly projectState: ProjectState }) {
  const candidates = safeArray(projectState.candidateArchitectures);
  if (candidates.length === 0) {
    return (
      <div className="p-6 text-sm text-dim">
        No candidate architectures generated yet.
      </div>
    );
  }
  return (
    <div className="p-6 space-y-4">
      {candidates.map((candidate, index) => (
        <div key={candidate.id ?? candidate.title ?? `candidate-${index}`} className="rounded-lg border border-border bg-card p-4">
          <div className="flex items-start gap-3">
            <div className="h-8 w-8 rounded-md bg-accent-soft flex items-center justify-center">
              <Layers className="h-4 w-4 text-accent" />
            </div>
            <div>
              <div className="text-sm font-semibold text-foreground">
                {candidate.title ?? "Untitled candidate"}
              </div>
              <div className="text-xs text-dim">{candidate.summary ?? ""}</div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function IterationEventsView({ projectState }: { readonly projectState: ProjectState }) {
  const events = safeArray(projectState.iterationEvents);
  if (events.length === 0) {
    return <div className="p-6 text-sm text-dim">No iteration events yet.</div>;
  }
  return (
    <div className="p-6 space-y-4">
      {events.map((eventItem) => (
        <div key={eventItem.id} className="rounded-lg border border-border bg-card p-4">
          <div className="flex items-start gap-3">
            <div className="h-8 w-8 rounded-md bg-accent-soft flex items-center justify-center">
              <MessageSquareQuote className="h-4 w-4 text-accent" />
            </div>
            <div>
              <div className="text-sm font-semibold text-foreground capitalize">{eventItem.kind}</div>
              <div className="text-xs text-dim">{eventItem.text}</div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function McpQueriesView({ projectState }: { readonly projectState: ProjectState }) {
  const queries = safeArray(projectState.mcpQueries);
  if (queries.length === 0) {
    return <div className="p-6 text-sm text-dim">No MCP queries recorded yet.</div>;
  }
  return (
    <div className="p-6 space-y-4">
      {queries.map((query) => (
        <div key={query.id} className="rounded-lg border border-border bg-card p-4">
          <div className="flex items-start gap-3">
            <div className="h-8 w-8 rounded-md bg-info-soft flex items-center justify-center">
              <FileSearch className="h-4 w-4 text-info" />
            </div>
            <div>
              <div className="text-sm font-semibold text-foreground">{query.queryText}</div>
              <div className="text-xs text-dim">{query.phase}</div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}


