/**
 * KB Job Status Component
 * Displays job status indicator and progress
 */

import { IngestionJob } from "../../types/ingestion";
import { KBMetrics } from "./KBMetrics";

interface KBJobStatusProps {
  job: IngestionJob;
}

export function KBJobStatus({ job }: KBJobStatusProps) {
  const isNotStarted = job.status === "not_started";

  if (isNotStarted) {
    return (
      <div className="mt-3 space-y-2">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-pill bg-gray-500" />
          <span className="text-sm font-medium text-gray-700">NOT STARTED</span>
          <span className="text-xs text-gray-500">Waiting to start</span>
        </div>
      </div>
    );
  }

  const statusIndicatorClass = `w-2 h-2 rounded-pill ${
    job.status === "running"
      ? "bg-status-running animate-pulse"
      : job.status === "paused"
        ? "bg-yellow-500"
        : job.status === "completed"
          ? "bg-status-completed"
          : job.status === "failed"
            ? "bg-status-failed"
            : "bg-gray-500"
  }`;

  const statusText =
    job.status === "completed"
      ? "COMPLETED"
      : job.status === "paused"
        ? "PAUSED"
        : `${job.phase ? job.phase.toUpperCase() : "UNKNOWN"} - ${typeof job.progress === "number" ? job.progress.toFixed(0) : "0"}%`;

  return (
    <div className="mt-3 space-y-2">
      <div className="flex items-center gap-2">
        <div className={statusIndicatorClass} />
        <span className="text-sm font-medium text-gray-700">{statusText}</span>
        {job.message && (
          <span className="text-xs text-gray-500">{job.message}</span>
        )}
      </div>

      {job.metrics && <KBMetrics metrics={job.metrics} />}
    </div>
  );
}
