import { useEffect, useMemo, useState, type ReactElement } from "react";
import { ListChecks, MessageSquareQuote, ShieldAlert, FileSearch, Layers, Waypoints } from "lucide-react";
import type { ProjectState, WafChecklist } from "../../../../../types/api";
import { checklistApi } from "../../../../../services/checklistService";
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
  const fallbackChecklist = useMemo(
    () => normalizeChecklist(projectState.wafChecklist),
    [projectState.wafChecklist],
  );
  const [checklist, setChecklist] = useState<WafChecklist>(fallbackChecklist);
  const [loading, setLoading] = useState(false);
  const projectId = projectState.projectId;

  useEffect(() => {
    let active = true;
    const loadNormalizedChecklist = async () => {
      if (projectId === "") {
        setChecklist(fallbackChecklist);
        return;
      }
      setLoading(true);
      try {
        const normalized = await checklistApi.fetchNormalizedChecklist(projectId);
        if (!active) {
          return;
        }
        setChecklist(normalized ?? fallbackChecklist);
      } catch {
        if (active) {
          setChecklist(fallbackChecklist);
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    void loadNormalizedChecklist();
    return () => {
      active = false;
    };
  }, [fallbackChecklist, projectId]);

  const checklistVersion = useMemo(() => checklist.version ?? "N/A", [checklist.version]);
  const progress = useMemo(() => computeWafProgress(checklist.items), [checklist.items]);

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center gap-3 justify-between">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-lg bg-blue-50 flex items-center justify-center">
            <ListChecks className="h-4 w-4 text-blue-600" />
          </div>
          <div>
            <p className="text-sm font-semibold text-gray-900">WAF Checklist</p>
            <p className="text-xs text-gray-500">Version {checklistVersion}</p>
          </div>
        </div>
        <div className="rounded-lg border border-blue-100 bg-blue-50 px-3 py-1.5">
          <div className="text-right">
            <p className="text-sm font-semibold text-gray-900">{progress.percentComplete}%</p>
            <p className="text-xs text-gray-500">
              {progress.covered}/{progress.total} covered
            </p>
          </div>
        </div>
      </div>
      <div className="grid grid-cols-3 gap-2 text-xs">
        <div className="rounded-md border border-green-200 bg-green-50 px-2 py-1 text-green-700">
          Covered: {progress.covered}
        </div>
        <div className="rounded-md border border-amber-200 bg-amber-50 px-2 py-1 text-amber-700">
          Partial: {progress.partial}
        </div>
        <div className="rounded-md border border-gray-200 bg-gray-50 px-2 py-1 text-gray-700">
          Not covered: {progress.notCovered}
        </div>
      </div>
      {loading ? (
        <div className="text-sm text-gray-500">Loading checklist...</div>
      ) : checklist.items.length === 0 ? (
        <div className="text-sm text-gray-500">
          No checklist items available yet. Completion baseline is 0%.
        </div>
      ) : (
        <div className="grid gap-3">
          {checklist.items.map((item) => (
            <div key={item.id} className="rounded-lg border border-gray-200 bg-white p-4">
              <div className="flex items-center justify-between gap-3">
                <div className="text-sm font-semibold text-gray-900">{item.pillar}</div>
                <WafStatusBadge status={getLatestWafEvaluation(item.evaluations)?.status ?? "notCovered"} />
              </div>
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

function getLatestWafEvaluation(
  evaluations: readonly WafChecklist["items"][number]["evaluations"][number][],
) {
  if (evaluations.length === 0) {
    return undefined;
  }

  return evaluations.reduce((latest, current) => {
    const latestTs = latest.createdAt !== undefined ? Date.parse(latest.createdAt) : Number.NEGATIVE_INFINITY;
    const currentTs = current.createdAt !== undefined ? Date.parse(current.createdAt) : Number.NEGATIVE_INFINITY;
    if (Number.isNaN(currentTs) && Number.isNaN(latestTs)) {
      return latest;
    }
    if (Number.isNaN(latestTs)) {
      return current;
    }
    if (Number.isNaN(currentTs)) {
      return latest;
    }
    return currentTs > latestTs ? current : latest;
  }, evaluations[0]);
}

function WafStatusBadge({ status }: { readonly status: "covered" | "partial" | "notCovered" }) {
  if (status === "covered") {
    return (
      <span className="rounded-full border border-green-200 bg-green-50 px-2 py-0.5 text-xs text-green-700">
        Covered
      </span>
    );
  }
  if (status === "partial") {
    return (
      <span className="rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-xs text-amber-700">
        Partial
      </span>
    );
  }
  return (
    <span className="rounded-full border border-gray-200 bg-gray-50 px-2 py-0.5 text-xs text-gray-700">
      Not covered
    </span>
  );
}

function computeWafProgress(items: readonly WafChecklist["items"][number][]) {
  let covered = 0;
  let partial = 0;
  let notCovered = 0;

  for (const item of items) {
    const latest = getLatestWafEvaluation(item.evaluations);
    const status = latest?.status ?? "notCovered";
    if (status === "covered") {
      covered += 1;
    } else if (status === "partial") {
      partial += 1;
    } else {
      notCovered += 1;
    }
  }

  const total = items.length;
  const percentComplete = total > 0 ? Math.round((covered / total) * 100) : 0;

  return {
    total,
    covered,
    partial,
    notCovered,
    percentComplete,
  };
}
