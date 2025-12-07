/**
 * React hook for polling ingestion job status
 */

import { useState, useEffect, useCallback } from "react";
import { IngestionJob } from "../types/ingestion";
import { getKBStatus } from "../services/ingestionApi";

interface UseIngestionJobOptions {
  pollInterval?: number; // milliseconds
  onComplete?: (job: IngestionJob) => void;
  onError?: (error: Error) => void;
  enabled?: boolean; // Whether to poll
}

interface UseIngestionJobReturn {
  job: IngestionJob | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

/**
 * Hook to poll ingestion job status for a KB
 */
export function useIngestionJob(
  kbId: string | null,
  options: UseIngestionJobOptions = {}
): UseIngestionJobReturn {
  const { pollInterval = 2000, onComplete, onError, enabled = true } = options;

  const [job, setJob] = useState<IngestionJob | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchStatus = useCallback(async () => {
    if (!kbId || !enabled) return;

    try {
      const data = await getKBStatus(kbId);
      setJob(data);
      setError(null);

      // Check if job completed
      if (data.status === "completed" && onComplete) {
        onComplete(data);
      } else if (data.status === "failed" && onError && data.error) {
        onError(new Error(data.error));
      }
    } catch (err) {
      const error =
        err instanceof Error ? err : new Error("Failed to fetch job status");
      setError(error);
      if (onError) onError(error);
    } finally {
      setLoading(false);
    }
  }, [kbId, enabled, onComplete, onError]);

  useEffect(() => {
    if (!kbId || !enabled) {
      setLoading(false);
      return;
    }

    let intervalId: NodeJS.Timeout | null = null;

    const startPolling = async () => {
      // Initial fetch
      await fetchStatus();

      // Set up polling only if job is running or pending/not_started
      intervalId = setInterval(async () => {
        const data = await getKBStatus(kbId);
        setJob(data);

        // Stop polling if job is completed, failed, or cancelled
        if (
          data.status === "completed" ||
          data.status === "failed" ||
          data.status === "cancelled" ||
          data.status === "not_started"
        ) {
          if (intervalId) {
            clearInterval(intervalId);
            intervalId = null;
          }
        }
      }, pollInterval);
    };

    void startPolling();

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [kbId, enabled, pollInterval]);

  return {
    job,
    loading,
    error,
    refetch: fetchStatus,
  };
}
