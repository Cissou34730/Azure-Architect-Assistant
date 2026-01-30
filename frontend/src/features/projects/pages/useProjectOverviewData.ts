import { ProjectState } from "../../../types/api";

function getProjectCounts(p: ProjectState) {
  return {
    requirements: p.requirements,
    adrs: p.adrs,
    findings: p.findings,
    iterationEvents: p.iterationEvents,
  };
}

function getLatestCostInfo(p: ProjectState) {
  const cost = p.costEstimates;
  const latest = cost.length > 0 ? (cost[cost.length - 1] ?? null) : null;
  return {
    monthlyCost: latest?.totalMonthlyCost ?? 0,
    currencyCode: latest?.currencyCode ?? "USD",
  };
}

export function useProjectOverviewData(projectState: ProjectState | null) {
  if (projectState === null) {
    return {
      requirements: [],
      adrs: [],
      findings: [],
      mindMapCoverage: null,
      iterationEvents: [],
      monthlyCost: 0,
      currencyCode: "USD",
      hasAnyData: false,
    };
  }

  const counts = getProjectCounts(projectState);
  const costInfo = getLatestCostInfo(projectState);

  const hasAnyData =
    counts.requirements.length > 0 ||
    counts.adrs.length > 0 ||
    counts.findings.length > 0 ||
    counts.iterationEvents.length > 0;

  return {
    ...counts,
    ...costInfo,
    mindMapCoverage: projectState.mindMapCoverage,
    hasAnyData,
  };
}
