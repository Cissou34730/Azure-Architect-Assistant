/**
 * React hook for polling ingestion job status
 */

import { useState, useEffect, useCallback } from "react";
import {
  IngestionJob,
  KBStatusSimple,
  KBIngestionDetails,
} from "../types/ingestion";
import {
  getKBReadyStatus,
  getKBIngestionDetails,
} from "../services/ingestionApi";

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

  function composeJob(
    kbIdLocal: string,
    status: KBStatusSimple,
    details?: KBIngestionDetails
  ): IngestionJob {
    const metrics = status.metrics || {};
    if (status.status === "not_ready") {
      return {
        job_id: `${kbIdLocal}-job`,
        kb_id: kbIdLocal,
        status: "not_started",
        phase: "loading",
        progress: 0,
        message: "Waiting to start",
        error: null,
        metrics: {
          chunks_pending: metrics.pending || 0,
          chunks_processing: metrics.processing || 0,
          chunks_embedded: metrics.done || 0,
          chunks_failed: metrics.error || 0,
          chunks_queued:
            (metrics.pending || 0) +
            (metrics.processing || 0) +
            (metrics.done || 0) +
            (metrics.error || 0),
        },
        started_at: new Date().toISOString(),
        completed_at: null,
        phase_details: details?.phase_details,
      };
    }
    if (status.status === "ready") {
      return {
        job_id: `${kbIdLocal}-job`,
        kb_id: kbIdLocal,
        status: "completed",
        phase: "completed",
        progress: 100,
        message: "Completed",
        error: null,
        metrics: {
          chunks_pending: metrics.pending || 0,
          chunks_processing: metrics.processing || 0,
          chunks_embedded: metrics.done || 0,
          chunks_failed: metrics.error || 0,
          chunks_queued:
            (metrics.pending || 0) +
            (metrics.processing || 0) +
            (metrics.done || 0) +
            (metrics.error || 0),
        },
        started_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
        phase_details: details?.phase_details,
      };
    }
    // pending
    return {
      job_id: `${kbIdLocal}-job`,
      kb_id: kbIdLocal,
      status: "pending",
      phase: (details?.current_phase || "loading") as IngestionJob["phase"],
      progress: details?.overall_progress ?? 0,
      message: "Ingestion in progress",
      error: null,
      metrics: {
        chunks_pending: metrics.pending || 0,
        chunks_processing: metrics.processing || 0,
        chunks_embedded: metrics.done || 0,
        chunks_failed: metrics.error || 0,
        chunks_queued:
          (metrics.pending || 0) +
          (metrics.processing || 0) +
          (metrics.done || 0) +
          (metrics.error || 0),
      },
      started_at: new Date().toISOString(),
      completed_at: null,
      phase_details: details?.phase_details,
    };
  }

  const fetchStatus = useCallback(async () => {
    if (!kbId || !enabled) return;

    try {
      const s = await getKBReadyStatus(kbId);
      let details: KBIngestionDetails | undefined;
      if (s.status === "pending") {
        details = await getKBIngestionDetails(kbId);
      }
      const composed = composeJob(kbId, s, details);
      setJob(composed);
      setError(null);

      // Check if job completed
      if (composed.status === "completed" && onComplete) {
        onComplete(composed);
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

      // Set up polling while status is pending
      intervalId = setInterval(async () => {
        const s = await getKBReadyStatus(kbId);
        let details: KBIngestionDetails | undefined;
        if (s.status === "pending") {
          details = await getKBIngestionDetails(kbId);
        }
        const composed = composeJob(kbId, s, details);
        setJob(composed);

        // Stop polling if job is completed or not_started
        if (composed.status === "completed" || composed.status === "not_started") {
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
