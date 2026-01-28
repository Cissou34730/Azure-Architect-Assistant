import { useMemo } from "react";
import { useProjectContext } from "../../projects/context/useProjectContext";
import type {
  TraceabilityLink,
  Requirement,
  MindMapCoverage,
  ProjectState,
} from "../../../types/api";

interface GroupedRequirements {
  readonly business: readonly Requirement[];
  readonly functional: readonly Requirement[];
  readonly nfr: readonly Requirement[];
  readonly other: readonly Requirement[];
}

function useGroupedRequirements(
  requirements: readonly Requirement[],
): GroupedRequirements {
  return useMemo((): GroupedRequirements => {
    const business: Requirement[] = [];
    const functional: Requirement[] = [];
    const nfr: Requirement[] = [];
    const other: Requirement[] = [];

    for (const req of requirements) {
      const category = (req.category ?? "").toLowerCase();
      if (category === "business") {
        business.push(req);
      } else if (category === "functional") {
        functional.push(req);
      } else if (category === "nfr") {
        nfr.push(req);
      } else {
        other.push(req);
      }
    }

    return { business, functional, nfr, other };
  }, [requirements]);
}

function useTraceabilityGroups(links: readonly TraceabilityLink[]) {
  return useMemo(() => {
    const groups: Record<string, TraceabilityLink[]> = {};
    for (const link of links) {
      const fromType = link.fromType.trim();
      const fromId = link.fromId.trim();
      const typeStr = fromType !== "" ? fromType : "unknown";
      const idStr = fromId !== "" ? fromId : "unknown";
      const key = `${typeStr}:${idStr}`;

      groups[key] ??= [];
      groups[key].push(link);
    }
    const sortedKeys = Object.keys(groups).sort((a, b) => a.localeCompare(b));
    return sortedKeys.map((k) => ({ key: k, links: groups[k] ?? [] }));
  }, [links]);
}

function useCoverageTopics(mindMapCoverage: MindMapCoverage | undefined) {
  return useMemo(() => {
    if (mindMapCoverage?.topics === undefined) {
      return [];
    }

    const entries = Object.entries(mindMapCoverage.topics).map(
      ([key, topicValue]) => ({
        key,
        status: topicValue.status,
      }),
    );

    const getOrder = (key: string): number => {
      const match = /^(\d+)_/.exec(key);
      return match !== null ? Number(match[1]) : 999;
    };

    return [...entries].sort((a, b) => {
      const orderA = getOrder(a.key);
      const orderB = getOrder(b.key);
      if (orderA !== orderB) return orderA - orderB;
      return a.key.localeCompare(b.key);
    });
  }, [mindMapCoverage]);
}

function useAaaProjectData(projectState: ProjectState | null | undefined) {
  return useMemo(() => {
    if (projectState === null || projectState === undefined) {
      return {
        requirements: [],
        clarificationQuestions: [],
        candidates: [],
        adrs: [],
        findings: [],
        iacArtifacts: [],
        costEstimates: [],
        iterationEvents: [],
        mindMapCoverage: undefined,
        traceabilityLinks: [],
        traceabilityIssues: [],
      };
    }

    return {
      requirements: projectState.requirements,
      clarificationQuestions: projectState.clarificationQuestions,
      candidates: projectState.candidateArchitectures,
      adrs: projectState.adrs,
      findings: projectState.findings,
      iacArtifacts: projectState.iacArtifacts,
      costEstimates: projectState.costEstimates,
      iterationEvents: projectState.iterationEvents,
      mindMapCoverage: projectState.mindMapCoverage,
      traceabilityLinks: projectState.traceabilityLinks,
      traceabilityIssues: projectState.traceabilityIssues,
    };
  }, [projectState]);
}

export function useAaaWorkspace() {
  const context = useProjectContext();
  const { projectState } = context;

  const data = useAaaProjectData(projectState);

  const coverageTopics = useCoverageTopics(data.mindMapCoverage);
  const traceabilityGroups = useTraceabilityGroups(data.traceabilityLinks);
  const groupedRequirements = useGroupedRequirements(data.requirements);

  const handleGenerateWorkspace = async () => {
    await context.handleAnalyzeDocuments();
  };

  return {
    ...context,
    ...data,
    coverageTopics,
    traceabilityGroups,
    groupedRequirements,
    handleGenerateWorkspace,
  };
}
