import { WafChecklist } from "../types/api";
import { API_BASE } from "./config";
import { fetchWithErrorHandling } from "./serviceError";

interface ChecklistSummaryApi {
  readonly id: string;
}

interface ChecklistItemDetailApi {
  readonly templateItemId: string;
  readonly title: string;
  readonly pillar: string | null;
  readonly latestEvaluation?: {
    readonly status?: string;
    readonly evaluator?: string;
    readonly timestamp?: string | null;
  } | null;
}

interface ChecklistDetailApi {
  readonly version?: string;
  readonly items: readonly ChecklistItemDetailApi[];
}

function mapNormalizedStatusToLegacy(status: string | undefined): "covered" | "partial" | "notCovered" {
  const normalized = (status ?? "").toLowerCase();
  if (normalized === "fixed" || normalized === "false_positive") {
    return "covered";
  }
  if (normalized === "in_progress") {
    return "partial";
  }
  return "notCovered";
}

export const checklistApi = {
  async fetchNormalizedChecklist(projectId: string): Promise<WafChecklist | null> {
    const summaries = await fetchWithErrorHandling<readonly ChecklistSummaryApi[]>(
      `${API_BASE}/projects/${projectId}/checklists`,
      {},
      "fetch normalized checklists",
    );

    if (summaries.length === 0) {
      return null;
    }

    const detail = await fetchWithErrorHandling<ChecklistDetailApi>(
      `${API_BASE}/projects/${projectId}/checklists/${summaries[0].id}`,
      {},
      "fetch normalized checklist detail",
    );

    const pillars = Array.from(
      new Set(
        detail.items
          .map((item) => item.pillar ?? "")
          .filter((pillar) => pillar !== ""),
      ),
    );

    return {
      version: detail.version,
      pillars,
      items: detail.items.map((item) => ({
        id: item.templateItemId,
        pillar: item.pillar ?? "General",
        topic: item.title,
        evaluations:
          item.latestEvaluation !== undefined && item.latestEvaluation !== null
            ? [
                {
                  id: `${item.templateItemId}-latest`,
                  status: mapNormalizedStatusToLegacy(item.latestEvaluation.status),
                  evidence: "",
                  relatedFindingIds: [],
                  sourceCitations: [],
                  createdAt: item.latestEvaluation.timestamp ?? undefined,
                },
              ]
            : [],
      })),
    };
  },
};
