import { JobMetrics } from "../../types/ingestion";
import { MetricCard } from "./MetricCard";

interface IngestionMetricsSectionProps {
  readonly metrics: JobMetrics;
}

function hasVisibleMetrics(metrics: JobMetrics): boolean {
  return (
    (metrics.documentsCrawled ?? 0) > 0 ||
    (metrics.chunksCreated ?? 0) > 0 ||
    (metrics.chunksProcessing ?? 0) > 0 ||
    (metrics.chunksFailed ?? 0) > 0 ||
    (metrics.chunksEmbedded ?? 0) > 0
  );
}

export function IngestionMetricsSection({
  metrics,
}: IngestionMetricsSectionProps) {
  if (!hasVisibleMetrics(metrics)) {
    return null;
  }

  return (
    <div className="space-y-3 pt-4 border-t">
      <h4 className="text-sm font-semibold text-secondary">Pipeline Metrics</h4>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {renderCrawledMetrics(metrics)}
        {renderProcessingMetrics(metrics)}
        {renderSuccessMetrics(metrics)}
      </div>
    </div>
  );
}

function renderCrawledMetrics(metrics: JobMetrics) {
  return (
    <>
      {metrics.documentsCrawled !== undefined && (
        <MetricCard
          label="Crawled"
          value={metrics.documentsCrawled}
          icon="[DOC]"
          color="blue"
        />
      )}
      {metrics.chunksCreated !== undefined && (
        <MetricCard
          label="Created"
          value={metrics.chunksCreated}
          icon="[CHNK]"
          color="indigo"
        />
      )}
    </>
  );
}

function renderProcessingMetrics(metrics: JobMetrics) {
  return (
    <>
      {metrics.chunksProcessing !== undefined && metrics.chunksProcessing > 0 && (
        <MetricCard
          label="In Progress"
          value={metrics.chunksProcessing}
          icon="[PRCS]"
          color="blue"
        />
      )}
      {metrics.chunksFailed !== undefined && metrics.chunksFailed > 0 && (
        <MetricCard
          label="Failed"
          value={metrics.chunksFailed}
          icon="[FAIL]"
          color="red"
        />
      )}
    </>
  );
}

function renderSuccessMetrics(metrics: JobMetrics) {
  if (metrics.chunksEmbedded === undefined || metrics.chunksQueued === undefined) {
    return null;
  }

  const progress = metrics.chunksQueued > 0
    ? (metrics.chunksEmbedded / metrics.chunksQueued) * 100
    : 0;

  return (
    <MetricCard
      label="Vectors"
      value={metrics.chunksEmbedded}
      total={metrics.chunksQueued}
      progress={progress}
      icon="[VEC]"
      color="pink"
    />
  );
}

