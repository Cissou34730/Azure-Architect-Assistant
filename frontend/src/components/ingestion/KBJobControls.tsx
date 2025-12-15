/**
 * KB Job Controls Component
 * Pause/Resume/Cancel controls for active jobs
 */

import { Button } from '../common';
import { pauseIngestion, resumeIngestion, cancelIngestion } from '../../services/ingestionApi';
import { useErrorHandler } from '../../hooks/useErrorHandler';

interface KBJobControlsProps {
  kbId: string;
  isRunning: boolean;
  isPaused: boolean;
  onRefresh: () => void;
  onViewProgress: (kbId: string) => void;
}

export function KBJobControls({ kbId, isRunning, isPaused, onRefresh, onViewProgress }: KBJobControlsProps) {
  const { handleError, toast } = useErrorHandler();

  const handlePause = async () => {
    try {
      await pauseIngestion(kbId);
      toast.success('Job paused successfully');
      onRefresh();
      onViewProgress(kbId);
    } catch (error) {
      handleError(error, { message: 'Failed to pause ingestion' });
    }
  };

  const handleResume = async () => {
    try {
      await resumeIngestion(kbId);
      toast.success('Job resumed successfully');
      onRefresh();
      onViewProgress(kbId);
    } catch (error) {
      handleError(error, { message: 'Failed to resume ingestion' });
    }
  };

  const handleCancel = async () => {
    try {
      await cancelIngestion(kbId);
      toast.success('Job cancelled successfully');
      onRefresh();
      onViewProgress(kbId);
    } catch (error) {
      handleError(error, { message: 'Failed to cancel ingestion' });
    }
  };

  return (
    <div className="flex gap-2">
      {isRunning && (
        <Button variant="ghost" size="sm" onClick={handlePause}>
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
