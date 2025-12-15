/**
 * React hook for polling ingestion job status
 */

import { useState, useEffect, useCallback, useRef } from "react";
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
  pollInterval?: number; // milliseconds for active jobs
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
  const DEFAULT_ACTIVE_POLL_MS = 5000;
  const IDLE_POLL_INTERVAL = 10000; // 10s health-check when idle
  const { pollInterval = DEFAULT_ACTIVE_POLL_MS, onComplete, onError, enabled = true } = options;

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

  function buildMetrics(
    status: KBStatusSimple,
    details?: KBIngestionDetails
  ): IngestionJob["metrics"] {
    const queue = status.metrics || {};
    const phases = details?.phase_details || [];

    const loadingPhase = phases.find((p) => p.name === "loading");
    const chunkingPhase = phases.find((p) => p.name === "chunking");
    const embeddingPhase = phases.find((p) => p.name === "embedding");
    const indexingPhase = phases.find((p) => p.name === "indexing");

    const chunksQueued =
      (queue.pending || 0) +
      (queue.processing || 0) +
      (queue.done || 0) +
      (queue.error || 0);

    return {
      documents_crawled: loadingPhase?.items_processed,
      documents_cleaned: chunkingPhase?.items_processed,
      chunks_created: chunkingPhase?.items_processed,
      chunks_queued: chunksQueued || chunkingPhase?.items_total,
      chunks_pending: queue.pending,
      chunks_processing: queue.processing,
      chunks_embedded:
        queue.done ||
        indexingPhase?.items_processed ||
        embeddingPhase?.items_processed,
      chunks_failed: queue.error,
    };
  }

  function composeJob(
    kbIdLocal: string,
    status: KBStatusSimple,
    details?: KBIngestionDetails
  ): IngestionJob {
    const composedMetrics = buildMetrics(status, details);

    const overallProgress =
      details?.overall_progress ??
      (status.status === "ready" ? 100 : 0);

    if (status.status === "not_ready") {
      return {
        job_id: `${kbIdLocal}-job`,
        kb_id: kbIdLocal,
        status: "not_started",
        phase: "loading",
        progress: overallProgress,
        message: "Waiting to start",
        error: null,
        metrics: composedMetrics,
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
        metrics: composedMetrics,
        started_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
        phase_details: details?.phase_details,
      };
    }
    // paused
    if (status.status === "paused") {
      return {
        job_id: `${kbIdLocal}-job`,
        kb_id: kbIdLocal,
        status: "paused",
        phase: (details?.current_phase || "loading") as IngestionJob["phase"],
        progress: overallProgress,
        message: "Ingestion paused",
        error: null,
        metrics: composedMetrics,
        started_at: new Date().toISOString(),
        completed_at: null,
        phase_details: details?.phase_details,
      };
    }
    // pending
    return {
      job_id: `${kbIdLocal}-job`,
      kb_id: kbIdLocal,
      status: "pending",
      phase: (details?.current_phase || "loading") as IngestionJob["phase"],
      progress: overallProgress,
      message: "Ingestion in progress",
      error: null,
      metrics: composedMetrics,
      started_at: new Date().toISOString(),
      completed_at: null,
      phase_details: details?.phase_details,
    };
  }

  const fetchStatus = useCallback(async (): Promise<IngestionJob | null> => {
    if (!kbId || !enabled) return null;

    try {
      const s = await getKBReadyStatus(kbId);
      let details: KBIngestionDetails | undefined;
      if (s.status === "pending" || s.status === "paused") {
        details = await getKBIngestionDetails(kbId);
      }
      const composed = composeJob(kbId, s, details);
      setJob(composed);
      setError(null);

      // Check if job completed
      if (composed.status === "completed" && onCompleteRef.current) {
        onCompleteRef.current(composed);
      }
      return composed;
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
    const run = async () => {
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

    void run();

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
