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
  if (job.status === "not_started") {
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

  const getStatusColorClass = () => {
    switch (job.status) {
      case "not_started":
      case "pending":
        return "bg-gray-400";
      case "running":
        return "bg-status-running animate-pulse";
      case "paused":
        return "bg-yellow-500";
      case "completed":
        return "bg-status-completed";
      case "failed":
        return "bg-status-failed";
    }
  };

  const statusText =
    job.status === "completed"
      ? "COMPLETED"
      : job.status === "paused"
        ? "PAUSED"
        : `${job.phase.toUpperCase()} - ${job.progress.toFixed(0)}%`;

  return (
    <div className="mt-3 space-y-2">
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-pill ${getStatusColorClass()}`} />
        <span className="text-sm font-medium text-gray-700">{statusText}</span>
        {job.message !== "" && (
          <span className="text-xs text-gray-500">{job.message}</span>
        )}
      </div>

      <KBMetrics metrics={job.metrics} />
    </div>
  );
}
