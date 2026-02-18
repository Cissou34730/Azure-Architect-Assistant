/**
 * Ingestion Progress Component
 * Displays real-time progress for an ingestion job
 */

import { IngestionJob } from "../../types/ingestion";
import { Button, StatusBadge, Card } from "../common";
import PhaseStatus from "./PhaseStatus";
import { PhaseTimeline } from "./PhaseTimeline";
import { IngestionActions } from "./IngestionActions";
import { IngestionMetricsSection } from "./IngestionMetricsSection";

interface IngestionProgressProps {
  readonly job: IngestionJob;
  readonly onStart?: () => void;
  readonly onRefresh?: () => void;
}

export function IngestionProgress({
  job,
  onStart,
  onRefresh,
}: IngestionProgressProps) {
  const isNotStarted = job.status === "not_started";
  const isPaused = job.status === "paused";

  // Render explicit Not Started state
  if (isNotStarted) {
    return (
      <Card className="space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-foreground">
            Ingestion Progress
          </h3>
          <StatusBadge variant="inactive">NOT STARTED</StatusBadge>
        </div>

        <div className="p-3 bg-surface border rounded-md text-sm text-secondary">
          Ingestion has not started yet.
        </div>

        <div className="flex justify-end gap-3 pt-2">
          {onStart !== undefined && (
            <Button variant="primary" onClick={onStart}>
              Start Ingestion
            </Button>
          )}
        </div>
      </Card>
    );
  }

  const getStatusVariant = () => {
    if (isPaused) return "paused";
    if (job.status === "running") return "running";
    if (job.status === "completed") return "completed";
    if (job.status === "failed") return "failed";
    return "inactive";
  };

  return (
    <Card className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-semibold text-foreground">
            Ingestion Progress
          </h3>
          <StatusBadge variant={getStatusVariant()}>
            {job.status.toUpperCase().replace("_", " ")}
          </StatusBadge>
        </div>
        {onRefresh !== undefined && (
          <Button variant="ghost" size="sm" onClick={onRefresh}>
            Refresh
          </Button>
        )}
      </div>

      <PhaseTimeline job={job} />

      {job.phaseDetails !== undefined && job.phaseDetails.length > 0 && (
        <div className="pt-4 border-t">
          <h4 className="text-sm font-semibold text-secondary mb-2">Phases</h4>
          <PhaseStatus phases={job.phaseDetails} />
        </div>
      )}

      <IngestionMetricsSection metrics={job.metrics} />

      {/* Error Display */}
      {job.error !== null && (
        <div className="p-3 bg-danger-soft border border-danger-line rounded-md">
          <div className="text-sm font-medium text-danger-strong">Error</div>
          <div className="text-sm text-danger mt-1">{job.error}</div>
        </div>
      )}

      <IngestionActions job={job} onRefresh={onRefresh} />

      {/* Timestamps */}
      <div className="flex justify-between text-xs text-dim pt-2 border-t">
        <div>Started: {new Date(job.startedAt).toLocaleString()}</div>
        {job.completedAt !== null && (
          <div>Completed: {new Date(job.completedAt).toLocaleString()}</div>
        )}
      </div>
    </Card>
  );
}


