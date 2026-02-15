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
          <div className="w-2 h-2 rounded-pill bg-dim" />
          <span className="text-sm font-medium text-secondary">NOT STARTED</span>
          <span className="text-xs text-dim">Waiting to start</span>
        </div>
      </div>
    );
  }

  const getStatusColorClass = () => {
    switch (job.status) {
      case "not_started":
      case "pending":
        return "bg-border-stronger";
      case "running":
        return "bg-status-running animate-pulse";
      case "paused":
        return "bg-warning-soft0";
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
        <span className="text-sm font-medium text-secondary">{statusText}</span>
        {job.message !== "" && (
          <span className="text-xs text-dim">{job.message}</span>
        )}
      </div>

      <KBMetrics metrics={job.metrics} />
    </div>
  );
}



