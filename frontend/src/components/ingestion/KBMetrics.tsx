/**
 * KB Metrics Component
 * Displays inline metrics for an ingestion job
 */

import { JobMetrics } from '../../types/ingestion';

interface KBMetricsProps {
  metrics: JobMetrics;
}

export function KBMetrics({ metrics }: KBMetricsProps) {
  return (
    <div className="flex items-center gap-4 text-xs">
      {metrics.documents_crawled !== undefined && metrics.documents_crawled > 0 && (
        <div className="flex items-center gap-1">
          <span className="text-gray-500">Docs:</span>
          <span className="font-semibold text-gray-700">{metrics.documents_crawled}</span>
        </div>
      )}
      {metrics.chunks_queued !== undefined && metrics.chunks_queued > 0 && (
        <div className="flex items-center gap-1">
          <span className="text-gray-500">Chunks:</span>
          <span className="font-semibold text-gray-700">{metrics.chunks_queued}</span>
        </div>
      )}
      {metrics.chunks_embedded !== undefined && metrics.chunks_embedded > 0 && (
        <div className="flex items-center gap-1">
          <span className="text-gray-500">Indexed:</span>
          <span className="font-semibold text-gray-700">
            {metrics.chunks_embedded}
            {metrics.chunks_queued && metrics.chunks_queued > 0 && (
              <>
                {' / '}
                {metrics.chunks_queued}
                <span className="text-gray-500 ml-1">
                  ({((metrics.chunks_embedded / metrics.chunks_queued) * 100).toFixed(0)}%)
                </span>
              </>
            )}
          </span>
        </div>
      )}
      {metrics.chunks_pending !== undefined && metrics.chunks_pending > 0 && (
        <div className="flex items-center gap-1">
          <span className="text-gray-500">Pending:</span>
          <span className="font-semibold text-yellow-600">{metrics.chunks_pending}</span>
        </div>
      )}
      {metrics.chunks_failed !== undefined && metrics.chunks_failed > 0 && (
        <div className="flex items-center gap-1">
          <span className="text-gray-500">Failed:</span>
          <span className="font-semibold text-red-600">{metrics.chunks_failed}</span>
        </div>
      )}
    </div>
  );
}
