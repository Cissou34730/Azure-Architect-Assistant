/**
 * React hook for polling ingestion job status
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { IngestionJob } from "../types/ingestion";
import { getKBJobView } from "../services/ingestionApi";
import { useCallbackRef } from "./useCallbackRef";

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

const DEFAULT_ACTIVE_POLL_MS = 5000;
const IDLE_POLL_INTERVAL = 10000;

function useIngestionJobSource(
  kbId: string | null,
  options: UseIngestionJobOptions
) {
  const { enabled = true } = options;
  const [job, setJob] = useState<IngestionJob | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const onCompleteRef = useCallbackRef(options.onComplete);
  const onErrorRef = useCallbackRef(options.onError);

  const fetchStatus = useCallback(async (): Promise<IngestionJob | null> => {
    if (kbId === null || !enabled) return null;

    try {
      const jobView = await getKBJobView(kbId);
      setJob(jobView);
      setError(null);

      if (
        jobView.status === "completed" &&
        onCompleteRef.current !== undefined
      ) {
        onCompleteRef.current(jobView);
      }
      return jobView;
    } catch (err) {
      const e =
        err instanceof Error ? err : new Error("Failed to fetch job status");
      setError(e);
      if (onErrorRef.current !== undefined) onErrorRef.current(e);
      return null;
    } finally {
      setLoading(false);
    }
  }, [kbId, enabled, onCompleteRef, onErrorRef]);

  return { job, loading, error, fetchStatus, setLoading };
}

/**
 * Hook to poll ingestion job status for a KB
 */
export function useIngestionJob(
  kbId: string | null,
  options: UseIngestionJobOptions = {}
): UseIngestionJobReturn {
  const { pollInterval = DEFAULT_ACTIVE_POLL_MS, enabled = true } = options;
  const { job, loading, error, fetchStatus, setLoading } =
    useIngestionJobSource(kbId, options);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const scheduleNext = async () => {
      if (kbId === null || !enabled) return;

      const composed = await fetchStatus();
      const active =
        composed?.status === "pending" || composed?.status === "paused";
      const nextDelay = active ? pollInterval : IDLE_POLL_INTERVAL;

      timeoutRef.current = setTimeout(() => {
        void scheduleNext();
      }, nextDelay);
    };

    if (kbId === null || !enabled) {
      setLoading(false);
    } else {
      void scheduleNext();
    }

    return () => {
      if (timeoutRef.current !== null) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [kbId, enabled, pollInterval, fetchStatus, setLoading]);

  return { job, loading, error, refetch: fetchStatus };
}
