export interface QualityGatePillarSummary {
  readonly pillar: string;
  readonly totalItems: number;
  readonly coveredItems: number;
  readonly partialItems: number;
  readonly notCoveredItems: number;
  readonly coveragePercentage: number;
}

export interface QualityGateWafSummary {
  readonly totalItems: number;
  readonly coveredItems: number;
  readonly partialItems: number;
  readonly notCoveredItems: number;
  readonly coveragePercentage: number;
  readonly pillars: readonly QualityGatePillarSummary[];
}

export interface QualityGateMindMapTopic {
  readonly key: string;
  readonly label: string;
  readonly status: string;
  readonly confidence: number;
}

export interface QualityGateMindMapSummary {
  readonly totalTopics: number;
  readonly addressedTopics: number;
  readonly partialTopics: number;
  readonly notAddressedTopics: number;
  readonly coveragePercentage: number;
  readonly topics: readonly QualityGateMindMapTopic[];
}

export interface QualityGateClarificationItem {
  readonly id: string;
  readonly question: string;
  readonly status: string;
  readonly priority?: number | null;
}

export interface QualityGateOpenClarifications {
  readonly count: number;
  readonly items: readonly QualityGateClarificationItem[];
}

export interface QualityGateMissingArtifact {
  readonly key: string;
  readonly label: string;
  readonly reason: string;
}

export interface QualityGateMissingArtifacts {
  readonly count: number;
  readonly items: readonly QualityGateMissingArtifact[];
}

export interface QualityGateTraceEventType {
  readonly eventType: string;
  readonly count: number;
}

export interface QualityGateTraceSummary {
  readonly totalEvents: number;
  readonly lastEventAt: string | null;
  readonly eventTypes: readonly QualityGateTraceEventType[];
}

export interface QualityGateReport {
  readonly generatedAt: string;
  readonly waf: QualityGateWafSummary;
  readonly mindMap: QualityGateMindMapSummary;
  readonly openClarifications: QualityGateOpenClarifications;
  readonly missingArtifacts: QualityGateMissingArtifacts;
  readonly trace: QualityGateTraceSummary;
}
