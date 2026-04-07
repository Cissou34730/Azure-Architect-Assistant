import { useEffect, useMemo, useState } from "react";
import type { WafChecklist } from "../../../types/api-artifacts";
import type { ProjectState } from "../../../types/api-project";
import { checklistApi } from "../../../api/checklistService";
import {
  ChecklistGroupTabs,
  WafChecklistHeader,
  WafChecklistPanel,
} from "./WafChecklistParts";
import type { WafChecklistGroup } from "./WafChecklistParts";

interface WafProgress {
  readonly total: number;
  readonly fixed: number;
  readonly inProgress: number;
  readonly open: number;
  readonly percentComplete: number;
}

function getLatestWafEvaluation(
  evaluations: readonly WafChecklist["items"][number]["evaluations"][number][],
) {
  if (evaluations.length === 0) return undefined;
  return evaluations.reduce((latest, current) => {
    const latestTs = latest.createdAt !== undefined ? Date.parse(latest.createdAt) : Number.NEGATIVE_INFINITY;
    const currentTs = current.createdAt !== undefined ? Date.parse(current.createdAt) : Number.NEGATIVE_INFINITY;
    if (Number.isNaN(latestTs)) return current;
    if (Number.isNaN(currentTs)) return latest;
    return currentTs > latestTs ? current : latest;
  }, evaluations[0]);
}

function computeWafProgress(items: readonly WafChecklist["items"][number][]): WafProgress {
  let fixed = 0;
  let inProgress = 0;
  let open = 0;
  for (const item of items) {
    const status = getLatestWafEvaluation(item.evaluations)?.status ?? "open";
    if (status === "fixed") fixed += 1;
    else if (status === "in_progress") inProgress += 1;
    else open += 1;
  }
  const total = items.length;
  return { total, fixed, inProgress, open, percentComplete: total > 0 ? Math.round((fixed / total) * 100) : 0 };
}

function checklistSortRank(title: string, key: string): number {
  const normalized = `${title} ${key}`.toLowerCase();
  if (normalized.includes("reliability")) return 0;
  if (normalized.includes("security")) return 1;
  if (normalized.includes("cost")) return 2;
  if (normalized.includes("operational")) return 3;
  if (normalized.includes("performance")) return 4;
  return 5;
}

function groupChecklistItems(items: readonly WafChecklist["items"][number][]): readonly WafChecklistGroup[] {
  const grouped = new Map<string, { checklistKey: string; checklistTitle: string; items: WafChecklist["items"][number][] }>();
  for (const item of items) {
    const key = item.templateSlug ?? item.checklistTitle ?? "waf";
    const title = item.checklistTitle ?? item.templateSlug ?? "WAF Checklist";
    const existing = grouped.get(key);
    if (existing === undefined) {
      grouped.set(key, { checklistKey: key, checklistTitle: title, items: [item] });
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

function useWafChecklist(projectState: ProjectState) {
  const emptyChecklist = useMemo<WafChecklist>(
    () => ({ items: [], pillars: [], version: undefined }),
    [],
  );
  const [checklist, setChecklist] = useState(emptyChecklist);
  const [loading, setLoading] = useState(false);
  const projectId = projectState.projectId;

  useEffect(() => {
    let active = true;
    const loadNormalizedChecklist = async () => {
      if (projectId === "") { setChecklist(emptyChecklist); return; }
      setChecklist(emptyChecklist);
      setLoading(true);
      try {
        const normalized = await checklistApi.fetchNormalizedChecklist(projectId);
        if (active) setChecklist(normalized ?? emptyChecklist);
      } catch {
        if (active) setChecklist(emptyChecklist);
      } finally {
        if (active) setLoading(false);
      }
    };
    void loadNormalizedChecklist();
    return () => { active = false; };
  }, [emptyChecklist, projectId]);

  return { checklist, loading };
}

function WafChecklistBody({ groupedItems }: { readonly groupedItems: readonly WafChecklistGroup[] }) {
  const [selectedChecklistKey, setSelectedChecklistKey] = useState("");
  const activeGroup = useMemo(
    () => groupedItems.find((g) => g.checklistKey === selectedChecklistKey) ?? groupedItems[0],
    [groupedItems, selectedChecklistKey],
  );

  return (
    <>
      <ChecklistGroupTabs
        groupedItems={groupedItems}
        selectedChecklistKey={activeGroup.checklistKey}
        onSelect={setSelectedChecklistKey}
      />
      <WafChecklistPanel group={activeGroup} />
    </>
  );
}

export function WafChecklistView({ projectState }: { readonly projectState: ProjectState }) {
  const { checklist, loading } = useWafChecklist(projectState);
  const checklistVersion = useMemo(() => checklist.version ?? "N/A", [checklist.version]);
  const progress = useMemo(() => computeWafProgress(checklist.items), [checklist.items]);
  const groupedItems = useMemo(() => groupChecklistItems(checklist.items), [checklist.items]);

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
        <WafChecklistBody groupedItems={groupedItems} />
      )}
    </div>
  );
}
