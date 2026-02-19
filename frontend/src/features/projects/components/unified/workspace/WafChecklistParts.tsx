import { CheckCircle2, Circle, MinusCircle } from "lucide-react";
import type { WafChecklist } from "../../../../../types/api";

interface WafChecklistGroup {
  readonly checklistKey: string;
  readonly checklistTitle: string;
  readonly items: readonly WafChecklist["items"][number][];
}

export type { WafChecklistGroup };

export function WafChecklistStatusIcon({
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

export function WafStatusBadge({
  status,
}: {
  readonly status: "covered" | "partial" | "notCovered";
}) {
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

export function WafSeverityBadge({
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

function getLatestStatus(
  evaluations: readonly WafChecklist["items"][number]["evaluations"][number][],
): "covered" | "partial" | "notCovered" {
  if (evaluations.length === 0) {
    return "notCovered";
  }
  const latest = evaluations.reduce((best, current) => {
    const bestTs = best.createdAt !== undefined ? Date.parse(best.createdAt) : Number.NEGATIVE_INFINITY;
    const currentTs = current.createdAt !== undefined ? Date.parse(current.createdAt) : Number.NEGATIVE_INFINITY;
    if (Number.isNaN(bestTs)) return current;
    if (Number.isNaN(currentTs)) return best;
    return currentTs > bestTs ? current : best;
  }, evaluations[0]);
  return latest.status;
}

export function WafChecklistRow({
  item,
}: {
  readonly item: WafChecklist["items"][number];
}) {
  const latestStatus = getLatestStatus(item.evaluations);
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

export function WafChecklistPanel({
  group,
}: {
  readonly group: WafChecklistGroup;
}) {
  const covered = group.items.filter((item) => getLatestStatus(item.evaluations) === "covered").length;
  return (
    <div className="rounded-xl border border-border bg-card">
      <div className="px-4 py-3 border-b border-border bg-muted flex items-center justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-foreground">{group.checklistTitle}</div>
          <div className="text-xs text-dim">{group.items.length} checks</div>
        </div>
        <div className="text-xs text-secondary">
          Covered {covered}/{group.items.length}
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

export function ChecklistGroupTabs({
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

interface WafProgress {
  readonly total: number;
  readonly covered: number;
  readonly partial: number;
  readonly notCovered: number;
  readonly percentComplete: number;
}

export function WafChecklistHeader({
  checklistVersion,
  progress,
}: {
  readonly checklistVersion: string;
  readonly progress: WafProgress;
}) {
  return (
    <>
      <div className="flex items-center gap-3 justify-between">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-lg bg-brand-soft flex items-center justify-center">
            <svg viewBox="0 0 24 24" className="h-4 w-4 text-brand" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" />
              <rect x="9" y="3" width="6" height="4" rx="1" />
              <path d="m9 12 2 2 4-4" />
            </svg>
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


