import { ListChecks, MessageSquareQuote, ShieldAlert, FileSearch, Layers, Waypoints } from "lucide-react";
import type { ProjectState, WafChecklist } from "../../../../../types/api";
import { RequirementsTab } from "../LeftContextPanel/RequirementsTab";
import { AssumptionsTab } from "../LeftContextPanel/AssumptionsTab";
import { QuestionsTab } from "../LeftContextPanel/QuestionsTab";
import { AdrLibrary, DiagramGallery, IacViewer, CostBreakdown } from "../../deliverables";
import { EmptyArtifactState } from "./EmptyArtifactState";
import type { ArtifactTab } from "./types";

interface ArtifactViewProps {
  readonly tabKind: ArtifactTab;
  readonly projectState: ProjectState;
  readonly hasArtifacts: boolean;
  readonly onGenerate: () => Promise<void>;
  readonly loading: boolean;
}

type ArtifactRenderer = (props: ArtifactViewProps) => JSX.Element;

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
  ["artifact-findings"]: ({ projectState, hasArtifacts, onGenerate, loading }) => (
    <FindingsList
      projectState={projectState}
      hasArtifacts={hasArtifacts}
      onGenerate={onGenerate}
      loading={loading}
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
  // eslint-disable-next-line @typescript-eslint/no-unsafe-return -- Renderer map is strongly typed via TypeScript.
  return artifactRenderers[props.tabKind](props);
}

interface FindingsListProps {
  readonly projectState: ProjectState;
  readonly hasArtifacts: boolean;
  readonly onGenerate: () => Promise<void>;
  readonly loading: boolean;
}

function FindingsList({
  projectState,
  hasArtifacts,
  onGenerate,
  loading,
}: FindingsListProps) {
  const findings = safeArray(projectState.findings);
  if (!hasArtifacts) {
    return (
      <EmptyArtifactState
        icon={ShieldAlert}
        title="No findings yet"
        description="Run an analysis to generate findings and gaps."
        onGenerate={onGenerate}
        loading={loading}
      />
    );
  }
  if (findings.length === 0) {
    return (
      <div className="p-6 text-sm text-gray-500">
        No findings available for this project.
      </div>
    );
  }
  return (
    <div className="p-6 space-y-4">
      {findings.map((finding) => (
        <div key={finding.id} className="rounded-lg border border-gray-200 bg-white p-4">
          <div className="flex items-start gap-3">
            <div className="h-8 w-8 rounded-md bg-amber-50 flex items-center justify-center">
              <ShieldAlert className="h-4 w-4 text-amber-600" />
            </div>
            <div>
              <div className="text-sm font-semibold text-gray-900">{finding.title}</div>
              <div className="text-xs text-gray-500">{finding.description}</div>
              <div className="mt-2 text-xs text-gray-600">{finding.remediation}</div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function WafChecklistView({ projectState }: { readonly projectState: ProjectState }) {
  const checklist = normalizeChecklist(projectState.wafChecklist);
  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center gap-3">
        <div className="h-9 w-9 rounded-lg bg-blue-50 flex items-center justify-center">
          <ListChecks className="h-4 w-4 text-blue-600" />
        </div>
        <div>
          <p className="text-sm font-semibold text-gray-900">WAF Checklist</p>
          <p className="text-xs text-gray-500">Version {checklist.version ?? "N/A"}</p>
        </div>
      </div>
      {checklist.items.length === 0 ? (
        <div className="text-sm text-gray-500">No checklist items available.</div>
      ) : (
        <div className="grid gap-3">
          {checklist.items.map((item) => (
            <div key={item.id} className="rounded-lg border border-gray-200 bg-white p-4">
              <div className="text-sm font-semibold text-gray-900">{item.pillar}</div>
              <div className="text-xs text-gray-500">{item.topic}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function TraceabilityView({ projectState }: { readonly projectState: ProjectState }) {
  const linkCount = safeArray(projectState.traceabilityLinks).length;
  const issueCount = safeArray(projectState.traceabilityIssues).length;
  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center gap-3">
        <div className="h-9 w-9 rounded-lg bg-cyan-50 flex items-center justify-center">
          <Waypoints className="h-4 w-4 text-cyan-600" />
        </div>
        <div>
          <p className="text-sm font-semibold text-gray-900">Traceability</p>
          <p className="text-xs text-gray-500">
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
      <div className="p-6 text-sm text-gray-500">
        No candidate architectures generated yet.
      </div>
    );
  }
  return (
    <div className="p-6 space-y-4">
      {candidates.map((candidate, index) => (
        <div key={candidate.id ?? candidate.title ?? `candidate-${index}`} className="rounded-lg border border-gray-200 bg-white p-4">
          <div className="flex items-start gap-3">
            <div className="h-8 w-8 rounded-md bg-indigo-50 flex items-center justify-center">
              <Layers className="h-4 w-4 text-indigo-600" />
            </div>
            <div>
              <div className="text-sm font-semibold text-gray-900">
                {candidate.title ?? "Untitled candidate"}
              </div>
              <div className="text-xs text-gray-500">{candidate.summary ?? ""}</div>
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
    return <div className="p-6 text-sm text-gray-500">No iteration events yet.</div>;
  }
  return (
    <div className="p-6 space-y-4">
      {events.map((eventItem) => (
        <div key={eventItem.id} className="rounded-lg border border-gray-200 bg-white p-4">
          <div className="flex items-start gap-3">
            <div className="h-8 w-8 rounded-md bg-violet-50 flex items-center justify-center">
              <MessageSquareQuote className="h-4 w-4 text-violet-600" />
            </div>
            <div>
              <div className="text-sm font-semibold text-gray-900 capitalize">{eventItem.kind}</div>
              <div className="text-xs text-gray-500">{eventItem.text}</div>
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
    return <div className="p-6 text-sm text-gray-500">No MCP queries recorded yet.</div>;
  }
  return (
    <div className="p-6 space-y-4">
      {queries.map((query) => (
        <div key={query.id} className="rounded-lg border border-gray-200 bg-white p-4">
          <div className="flex items-start gap-3">
            <div className="h-8 w-8 rounded-md bg-emerald-50 flex items-center justify-center">
              <FileSearch className="h-4 w-4 text-emerald-600" />
            </div>
            <div>
              <div className="text-sm font-semibold text-gray-900">{query.queryText}</div>
              <div className="text-xs text-gray-500">{query.phase}</div>
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

function normalizeChecklist(value: WafChecklist | undefined): WafChecklist {
  if (value === undefined) {
    return { items: [], pillars: [], version: undefined };
  }
  return value;
}
