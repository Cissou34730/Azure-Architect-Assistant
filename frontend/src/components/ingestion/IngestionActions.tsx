import { IngestionJob } from "../../types/ingestion";
import { Button } from "../common";
import {
  pauseIngestion,
  resumeIngestion,
  cancelIngestion,
} from "../../services/ingestionApi";

interface IngestionActionsProps {
  readonly job: IngestionJob;
  readonly onRefresh?: () => void;
}

export function IngestionActions({ job, onRefresh }: IngestionActionsProps) {
  const isPaused = job.status === "paused";
  const isRunning = job.status === "running" || job.status === "pending";

  const handleAction = async <T,>(
    action: (id: string) => Promise<T>
  ): Promise<void> => {
    try {
      await action(job.jobId);
      onRefresh?.();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Action failed";
      console.error("Ingestion action failed:", message);
    }
  };

  return (
    <div className="flex justify-end gap-3 pt-6 border-t">
      <Button
        variant="danger"
        size="sm"
        onClick={() => {
          if (confirm("Cancel ingestion?")) {
            void handleAction(cancelIngestion);
          }
        }}
      >
        Cancel
      </Button>
      {isPaused ? (
        <Button
          variant="primary"
          size="sm"
          onClick={() => void handleAction(resumeIngestion)}
        >
          Resume
        </Button>
      ) : (
        isRunning && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => void handleAction(pauseIngestion)}
          >
            Pause
          </Button>
        )
      )}
    </div>
  );
}
