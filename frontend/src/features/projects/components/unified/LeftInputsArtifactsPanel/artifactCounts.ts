export interface ArtifactCounts {
  readonly requirements: number;
  readonly assumptions: number;
  readonly questions: number;
  readonly adrs: number;
  readonly diagrams: number;
  readonly findings: number;
  readonly costs: number;
  readonly iac: number;
  readonly waf: number;
  readonly traceabilityLinks: number;
  readonly traceabilityIssues: number;
  readonly candidates: number;
  readonly iterations: number;
  readonly mcpQueries: number;
}

export function getArtifactTotal(artifacts: ArtifactCounts) {
  return (
    artifacts.requirements +
    artifacts.assumptions +
    artifacts.questions +
    artifacts.adrs +
    artifacts.diagrams +
    artifacts.findings +
    artifacts.costs +
    artifacts.iac +
    artifacts.waf +
    artifacts.traceabilityLinks +
    artifacts.traceabilityIssues +
    artifacts.candidates +
    artifacts.iterations +
    artifacts.mcpQueries
  );
}
