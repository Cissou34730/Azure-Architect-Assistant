import { IngestionJob } from "../../types/ingestion";
import { Button } from "../common";
import {
  pauseIngestion,
  resumeIngestion,
  cancelIngestion,
} from "../../services/ingestionApi";
import { useErrorHandler } from "../../hooks/useErrorHandler";

interface IngestionActionsProps {
  readonly job: IngestionJob;
  readonly onRefresh?: () => void;
}

export function IngestionActions({ job, onRefresh }: IngestionActionsProps) {
  const isPaused = job.status === "paused";
  const isRunning = job.status === "running" || job.status === "pending";
  const { handleError, toast } = useErrorHandler();

  const handlePause = async () => {
    try {
      await pauseIngestion(job.kbId);
      toast.success("Job paused successfully");
      onRefresh?.();
    } catch (error) {
      handleError(error, { message: "Failed to pause ingestion" });
    }
  };

  const handleResume = async () => {
    try {
      await resumeIngestion(job.kbId);
      toast.success("Job resumed successfully");
      onRefresh?.();
    } catch (error) {
      handleError(error, { message: "Failed to resume ingestion" });
    }
  };

  const handleCancel = async () => {
    if (!confirm("Cancel ingestion? This action cannot be undone.")) {
      return;
    }
    try {
      await cancelIngestion(job.kbId);
      toast.success("Job cancelled successfully");
      onRefresh?.();
    } catch (error) {
      handleError(error, { message: "Failed to cancel ingestion" });
    }
  };

  return (
    <div className="flex justify-end gap-3 pt-6 border-t">
      {isRunning && (
        <Button variant="warning" size="sm" onClick={handlePause}>
          Pause
        </Button>
      )}
      {isPaused && (
        <Button variant="success" size="sm" onClick={handleResume}>
          Resume
        </Button>
      )}
      {(isRunning || isPaused) && (
        <Button variant="danger" size="sm" onClick={handleCancel}>
          Cancel
        </Button>
      )}
    </div>
  );
}
