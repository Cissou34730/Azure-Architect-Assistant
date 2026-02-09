import { WafChecklist } from "../types/api";
import { API_BASE } from "./config";
import { fetchWithErrorHandling } from "./serviceError";

interface ChecklistSummaryApi {
  readonly id: string;
  readonly title: string;
  readonly templateSlug?: string | null;
}

interface ChecklistItemDetailApi {
  readonly templateItemId: string;
  readonly title: string;
  readonly description?: string | null;
  readonly pillar: string | null;
  readonly severity?: "low" | "medium" | "high" | "critical";
  readonly guidance?: Record<string, unknown> | null;
  readonly itemMetadata?: Record<string, unknown> | null;
  readonly latestEvaluation?: {
    readonly status?: string;
    readonly evaluator?: string;
    readonly timestamp?: string | null;
  } | null;
}

interface ChecklistDetailApi {
  readonly title: string;
  readonly version?: string;
  readonly templateSlug?: string | null;
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
    const summaries = await fetchChecklistSummaries(projectId);
    if (summaries.length === 0) {
      return null;
    }

    const details = await fetchChecklistDetails(projectId, summaries);

    return {
      version: resolveVersion(details),
      pillars: collectPillars(details),
      items: collectChecklistItems(details),
    };
  },
};

async function fetchChecklistSummaries(projectId: string): Promise<readonly ChecklistSummaryApi[]> {
  return fetchWithErrorHandling<readonly ChecklistSummaryApi[]>(
    `${API_BASE}/projects/${projectId}/checklists`,
    {},
    "fetch normalized checklists",
  );
}

async function fetchChecklistDetails(
  projectId: string,
  summaries: readonly ChecklistSummaryApi[],
): Promise<readonly ChecklistDetailApi[]> {
  return Promise.all(
    summaries.map(async (summary) =>
      fetchWithErrorHandling<ChecklistDetailApi>(
        `${API_BASE}/projects/${projectId}/checklists/${summary.id}`,
        {},
        "fetch normalized checklist detail",
      ),
    ),
  );
}

function collectPillars(details: readonly ChecklistDetailApi[]): readonly string[] {
  return Array.from(
    new Set(
      details
        .flatMap((detail) => detail.items.map((item) => item.pillar ?? ""))
        .filter((pillar) => pillar.trim() !== ""),
    ),
  );
}

function collectChecklistItems(
  details: readonly ChecklistDetailApi[],
): WafChecklist["items"] {
  return details.flatMap((detail) =>
    detail.items.map((item) => ({
      id: `${detail.templateSlug ?? "template"}:${item.templateItemId}`,
      pillar: item.pillar ?? "General",
      topic: item.title,
      description: item.description ?? undefined,
      severity: item.severity,
      guidance: extractGuidanceSteps(item.guidance, item.itemMetadata),
      checklistTitle: detail.title,
      templateSlug: detail.templateSlug ?? undefined,
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
  );
}

function resolveVersion(details: readonly ChecklistDetailApi[]): string | undefined {
  const versions = Array.from(
    new Set(details.map((detail) => detail.version).filter((value): value is string => value !== undefined)),
  );
  if (versions.length === 1) {
    return versions[0];
  }
  if (versions.length > 1) {
    return "multiple";
  }
  return undefined;
}

function extractGuidanceSteps(
  guidance: Record<string, unknown> | null | undefined,
  metadata: Record<string, unknown> | null | undefined,
): readonly string[] {
  const fromGuidance = tryExtractStringList(guidance, "checks");
  if (fromGuidance.length > 0) {
    return fromGuidance;
  }

  const fromMetadata = tryExtractStringList(metadata, "checks");
  if (fromMetadata.length > 0) {
    return fromMetadata;
  }

  const recommendation = tryExtractString(guidance, "recommendation");
  if (recommendation !== null) {
    return [recommendation];
  }

  return [];
}

function tryExtractStringList(
  value: Record<string, unknown> | null | undefined,
  key: string,
): readonly string[] {
  if (value === null || value === undefined) {
    return [];
  }
  const candidate = value[key];
  if (!Array.isArray(candidate)) {
    return [];
  }
  return candidate.filter((item): item is string => typeof item === "string" && item.trim() !== "");
}

function tryExtractString(
  value: Record<string, unknown> | null | undefined,
  key: string,
): string | null {
  if (value === null || value === undefined) {
    return null;
  }
  const candidate = value[key];
  if (typeof candidate !== "string" || candidate.trim() === "") {
    return null;
  }
  return candidate;
}
