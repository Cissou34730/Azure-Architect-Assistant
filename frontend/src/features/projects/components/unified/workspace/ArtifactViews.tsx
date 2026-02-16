import { useEffect, useMemo, useState, type ReactElement } from "react";
import {
  CheckCircle2,
  Circle,
  ListChecks,
  MessageSquareQuote,
  MinusCircle,
  ShieldAlert,
  FileSearch,
  Layers,
  Waypoints,
} from "lucide-react";
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

function WafChecklistView({ projectState }: { readonly projectState: ProjectState }) {
  const { checklist, loading } = useWafChecklist(projectState);
  const checklistVersion = useMemo(() => checklist.version ?? "N/A", [checklist.version]);
  const progress = useMemo(() => computeWafProgress(checklist.items), [checklist.items]);
  const groupedItems = useMemo(() => groupChecklistItems(checklist.items), [checklist.items]);
  const [selectedChecklistKey, setSelectedChecklistKey] = useState<string>("");
  const activeGroup = useMemo(
    () => groupedItems.find((group) => group.checklistKey === selectedChecklistKey) ?? groupedItems[0],
    [groupedItems, selectedChecklistKey],
  );

  return (
    <div className="p-6 space-y-4">
      <WafChecklistHeader checklistVersion={checklistVersion} progress={progress} />
      {loading ? (
        <div className="text-sm text-dim">Loading checklist...</div>
      ) : checklist.items.length === 0 ? (
        <div className="text-sm text-dim">
          No checklist items available yet. Completion baseline is 0%.
        </div>
      ) : (
        <>
          <ChecklistGroupTabs
            groupedItems={groupedItems}
            selectedChecklistKey={activeGroup.checklistKey}
            onSelect={setSelectedChecklistKey}
          />
          <WafChecklistPanel group={activeGroup} />
        </>
      )}
    </div>
  );
}

function useWafChecklist(projectState: ProjectState) {
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
      // Apply latest state-derived checklist immediately; normalized fetch then reconciles.
      setChecklist(fallbackChecklist);
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

  return { checklist, loading };
}

function WafChecklistHeader({
  checklistVersion,
  progress,
}: {
  readonly checklistVersion: string;
  readonly progress: ReturnType<typeof computeWafProgress>;
}) {
  return (
    <>
      <div className="flex items-center gap-3 justify-between">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-lg bg-brand-soft flex items-center justify-center">
            <ListChecks className="h-4 w-4 text-brand" />
          </div>
          <div>
            <p className="text-sm font-semibold text-foreground">WAF Checklist</p>
            <p className="text-xs text-dim">Version {checklistVersion}</p>
          </div>
        </div>
        <div className="rounded-lg border border-brand-line bg-brand-soft px-3 py-1.5">
          <div className="text-right">
            <p className="text-sm font-semibold text-foreground">{progress.percentComplete}%</p>
            <p className="text-xs text-dim">
              {progress.covered}/{progress.total} covered
            </p>
          </div>
        </div>
      </div>
      <div className="grid grid-cols-3 gap-2 text-xs">
        <div className="rounded-md border border-success-line bg-success-soft px-2 py-1 text-success">
          Covered: {progress.covered}
        </div>
        <div className="rounded-md border border-warning-line bg-warning-soft px-2 py-1 text-warning">
          Partial: {progress.partial}
        </div>
        <div className="rounded-md border border-border bg-surface px-2 py-1 text-secondary">
          Not covered: {progress.notCovered}
        </div>
      </div>
    </>
  );
}

function ChecklistGroupTabs({
  groupedItems,
  selectedChecklistKey,
  onSelect,
}: {
  readonly groupedItems: readonly WafChecklistGroup[];
  readonly selectedChecklistKey: string;
  readonly onSelect: (key: string) => void;
}) {
  return (
    <div className="overflow-x-auto pb-1">
      <div className="flex items-center gap-2 min-w-max">
        {groupedItems.map((group) => (
          <button
            key={group.checklistKey}
            type="button"
            onClick={() => {
              onSelect(group.checklistKey);
            }}
            className={
              group.checklistKey === selectedChecklistKey
                ? "rounded-lg border border-brand-line bg-brand-soft px-3 py-2 text-left"
                : "rounded-lg border border-border bg-card px-3 py-2 text-left hover:bg-surface"
            }
          >
            <div className="text-xs font-semibold text-foreground whitespace-nowrap">
              {group.checklistTitle}
            </div>
            <div className="text-xs text-dim whitespace-nowrap">{group.items.length} checks</div>
          </button>
        ))}
      </div>
    </div>
  );
}

function WafChecklistPanel({
  group,
}: {
  readonly group: WafChecklistGroup;
}) {
  const progress = useMemo(() => computeWafProgress(group.items), [group.items]);

  return (
    <div className="rounded-xl border border-border bg-card">
      <div className="px-4 py-3 border-b border-border bg-muted flex items-center justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-foreground">{group.checklistTitle}</div>
          <div className="text-xs text-dim">{group.items.length} checks</div>
        </div>
        <div className="text-xs text-secondary">
          Covered {progress.covered}/{progress.total}
        </div>
      </div>
      <div className="max-h-[56vh] overflow-y-auto p-3 space-y-2">
        {group.items.map((item) => (
          <WafChecklistRow key={item.id} item={item} />
        ))}
      </div>
    </div>
  );
}

function WafChecklistRow({ item }: { readonly item: WafChecklist["items"][number] }) {
  const latestStatus = getLatestWafEvaluation(item.evaluations)?.status ?? "notCovered";
  return (
    <div className="rounded-lg border border-border bg-card p-3">
      <div className="flex items-start gap-3">
        <div className="mt-0.5">
          <WafChecklistStatusIcon status={latestStatus} />
        </div>
        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex items-center justify-between gap-3">
            <div className="text-sm font-semibold text-foreground">{item.topic}</div>
            <WafStatusBadge status={latestStatus} />
          </div>
          <div className="flex items-center gap-2 text-xs text-dim">
            <span>{item.pillar}</span>
            {item.severity !== undefined && <WafSeverityBadge severity={item.severity} />}
          </div>
          {item.description !== undefined && item.description !== "" && (
            <div className="text-xs text-secondary">{item.description}</div>
          )}
          {item.guidance !== undefined && item.guidance.length > 0 && (
            <ul className="list-disc pl-4 text-xs text-secondary space-y-1">
              {item.guidance.map((step) => (
                <li key={`${item.id}-${step}`}>{step}</li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

function WafChecklistStatusIcon({
  status,
}: {
  readonly status: "covered" | "partial" | "notCovered";
}) {
  if (status === "covered") {
    return <CheckCircle2 className="h-4 w-4 text-success" />;
  }
  if (status === "partial") {
    return <MinusCircle className="h-4 w-4 text-warning" />;
  }
  return <Circle className="h-4 w-4 text-dim" />;
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
      <span className="rounded-full border border-success-line bg-success-soft px-2 py-0.5 text-xs text-success">
        Covered
      </span>
    );
  }
  if (status === "partial") {
    return (
      <span className="rounded-full border border-warning-line bg-warning-soft px-2 py-0.5 text-xs text-warning">
        Partial
      </span>
    );
  }
  return (
    <span className="rounded-full border border-border bg-surface px-2 py-0.5 text-xs text-secondary">
      Not covered
    </span>
  );
}

function WafSeverityBadge({
  severity,
}: {
  readonly severity: "low" | "medium" | "high" | "critical";
}) {
  if (severity === "critical") {
    return (
      <span className="rounded-full border border-danger-line bg-danger-soft px-2 py-0.5 text-xs text-danger-strong">
        Critical
      </span>
    );
  }
  if (severity === "high") {
    return (
      <span className="rounded-full border border-warning-line bg-warning-soft px-2 py-0.5 text-xs text-warning">
        High
      </span>
    );
  }
  if (severity === "medium") {
    return (
      <span className="rounded-full border border-warning-line bg-warning-soft px-2 py-0.5 text-xs text-warning">
        Medium
      </span>
    );
  }
  return (
    <span className="rounded-full border border-border bg-muted px-2 py-0.5 text-xs text-secondary">
      Low
    </span>
  );
}

interface WafChecklistGroup {
  readonly checklistKey: string;
  readonly checklistTitle: string;
  readonly items: readonly WafChecklist["items"][number][];
}

function groupChecklistItems(items: readonly WafChecklist["items"][number][]): readonly WafChecklistGroup[] {
  const grouped = new Map<string, {
    checklistKey: string;
    checklistTitle: string;
    items: WafChecklist["items"][number][];
  }>();

  for (const item of items) {
    const key = item.templateSlug ?? item.checklistTitle ?? "waf";
    const title = item.checklistTitle ?? item.templateSlug ?? "WAF Checklist";
    const existing = grouped.get(key);
    if (existing === undefined) {
      grouped.set(key, {
        checklistKey: key,
        checklistTitle: title,
        items: [item],
      });
      continue;
    }
    existing.items.push(item);
  }

  return Array.from(grouped.values()).sort(
    (left, right) =>
      checklistSortRank(left.checklistTitle, left.checklistKey) -
      checklistSortRank(right.checklistTitle, right.checklistKey),
  );
}

function checklistSortRank(title: string, key: string): number {
  const normalized = `${title} ${key}`.toLowerCase();
  if (normalized.includes("reliability")) {
    return 0;
  }
  if (normalized.includes("security")) {
    return 1;
  }
  if (normalized.includes("cost")) {
    return 2;
  }
  if (normalized.includes("operational")) {
    return 3;
  }
  if (normalized.includes("performance")) {
    return 4;
  }
  return 5;
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


