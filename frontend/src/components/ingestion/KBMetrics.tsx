/**
 * KB Metrics Component
 * Displays inline metrics for an ingestion job
 */

import { JobMetrics } from "../../types/ingestion";

interface KBMetricsProps {
  metrics: JobMetrics;
}

export function KBMetrics({ metrics }: KBMetricsProps) {
  const renderSimpleMetric = (label: string, value: number | undefined) => {
    if (value === undefined || value <= 0) {
      return null;
    }
    return (
      <div className="flex items-center gap-1">
        <span className="text-gray-500">{label}:</span>
        <span className="font-semibold text-gray-700">{value}</span>
      </div>
    );
  };

  const renderEmbeddedMetric = () => {
    const embedded = metrics.chunksEmbedded;
    const queued = metrics.chunksQueued;

    if (embedded === undefined || embedded <= 0) {
      return null;
    }

    return (
      <div className="flex items-center gap-1">
        <span className="text-gray-500">Indexed:</span>
        <span className="font-semibold text-gray-700">
          {embedded}
          {queued !== undefined && queued > 0 && (
            <>
              {" / "}
              {queued}
              <span className="text-gray-500 ml-1">
                ({((embedded / queued) * 100).toFixed(0)}%)
              </span>
            </>
          )}
        </span>
      </div>
    );
  };

  const renderFailedMetric = () => {
    if (metrics.chunksFailed === undefined || metrics.chunksFailed <= 0) {
      return null;
    }
    return (
      <div className="flex items-center gap-1">
        <span className="text-gray-500">Failed:</span>
        <span className="font-semibold text-red-600">
          {metrics.chunksFailed}
        </span>
      </div>
    );
  };

  return (
    <div className="flex items-center gap-4 text-xs">
      {renderSimpleMetric("Queued", metrics.chunksQueued)}
      {renderSimpleMetric("Docs", metrics.documentsCrawled)}
      {renderSimpleMetric("Cleaned", metrics.documentsCleaned)}
      {renderSimpleMetric("Chunks", metrics.chunksCreated)}
      {renderEmbeddedMetric()}
      {renderSimpleMetric("Processing", metrics.chunksProcessing)}
      {renderSimpleMetric("Pending", metrics.chunksPending)}
      {renderFailedMetric()}
    </div>
  );
}
