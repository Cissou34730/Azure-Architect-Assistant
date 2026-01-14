/**
 * React hook for polling ingestion job status
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { IngestionJob } from "../types/ingestion";
import { getKBJobView } from "../services/ingestionApi";

interface UseIngestionJobOptions {
  pollInterval?: number; // milliseconds for active jobs
  onComplete?: (job: IngestionJob) => void;
  onError?: (error: Error) => void;
  enabled?: boolean; // Whether to poll
}

interface UseIngestionJobReturn {
  job: IngestionJob | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<IngestionJob | null>;
}

/**
 * Hook to poll ingestion job status for a KB
 */
export function useIngestionJob(
  kbId: string | null,
  options: UseIngestionJobOptions = {},
): UseIngestionJobReturn {
  const DEFAULT_ACTIVE_POLL_MS = 5000;
  const IDLE_POLL_INTERVAL = 10000; // 10s health-check when idle
  const {
    pollInterval = DEFAULT_ACTIVE_POLL_MS,
    onComplete,
    onError,
    enabled = true,
  } = options;

  const [job, setJob] = useState<IngestionJob | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const onCompleteRef = useRef<typeof onComplete>(onComplete);
  const onErrorRef = useRef<typeof onError>(onError);

  // Keep callback refs in sync without recreating effects
  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  const fetchStatus = useCallback(async (): Promise<IngestionJob | null> => {
    if (!kbId || !enabled) return null;

    try {
      const jobView = await getKBJobView(kbId);
      setJob(jobView);
      setError(null);

      // Check if job completed
      if (jobView.status === "completed" && onCompleteRef.current) {
        onCompleteRef.current(jobView);
      }
      return jobView;
    } catch (err) {
      const error =
        err instanceof Error ? err : new Error("Failed to fetch job status");
      setError(error);
      if (onErrorRef.current) onErrorRef.current(error);
      return null;
    } finally {
      setLoading(false);
    }
  }, [kbId, enabled]);

  useEffect(() => {
    const run = () => {
      if (!kbId || !enabled) {
        setLoading(false);
        return;
      }

      // Clear any existing timer before starting a new loop
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }

      const scheduleNext = async () => {
        // If polling disabled or kbId missing, bail
        if (!kbId || !enabled) {
          return;
        }

        const composed = await fetchStatus();
        // Decide next delay: fast while running/paused, slow otherwise
        const active =
          composed?.status === "pending" || composed?.status === "paused";
        const nextDelay = active ? pollInterval : IDLE_POLL_INTERVAL;

        timeoutRef.current = setTimeout(() => {
          void scheduleNext();
        }, nextDelay);
      };

      // Kick off polling loop
      void scheduleNext();
    };

    run();

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    };
  }, [kbId, enabled, pollInterval, fetchStatus]);

  return {
    job,
    loading,
    error,
    refetch: fetchStatus,
  };
}
