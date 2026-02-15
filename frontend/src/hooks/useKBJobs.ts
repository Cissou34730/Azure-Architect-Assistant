import { useState, useCallback, useEffect, useRef } from "react";
import { KnowledgeBase, IngestionJob } from "../types/ingestion";
import { getKBJobView } from "../services/ingestionApi";

function extractJobStatus(results: { id: string; job: IngestionJob }[]) {
  const jobsMap = new Map<string, IngestionJob>();
  let hasActive = false;
  results.forEach((res) => {
    jobsMap.set(res.id, res.job);
    if (["pending", "running", "paused"].includes(res.job.status)) {
      hasActive = true;
    }
  });
  return { jobsMap, hasActive };
}

export function useKBJobs(kbs: readonly KnowledgeBase[]) {
  const [jobs, setJobs] = useState<Map<string, IngestionJob>>(new Map());
  const [loading, setLoading] = useState(true);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inFlightRef = useRef(false);

  const fetchJobs = useCallback(async () => {
    if (inFlightRef.current) return false;
    inFlightRef.current = true;
    try {
      const results = await Promise.all(
        kbs.map(async (kb) => {
          try {
            return { id: kb.id, job: await getKBJobView(kb.id) };
          } catch {
            return null;
          }
        })
      );
      const validResults = results.filter(
        (r): r is { id: string; job: IngestionJob } => r !== null
      );
      const { jobsMap, hasActive } = extractJobStatus(validResults);
      setJobs(jobsMap);
      return hasActive;
    } catch (error) {
      console.error("Failed to fetch KB statuses:", error);
      return false;
    } finally {
      setLoading(false);
      inFlightRef.current = false;
    }
  }, [kbs]);

  useEffect(() => {
    let cancelled = false;
    const loop = async () => {
      if (cancelled) return;
      const hasActive = await fetchJobs();
      timeoutRef.current = setTimeout(
        () => void loop(),
        hasActive ? 5000 : 10000
      );
    };
    void loop();
    return () => {
      cancelled = true;
      if (timeoutRef.current !== null) clearTimeout(timeoutRef.current);
    };
  }, [fetchJobs]);

  return { jobs, loading, refetch: fetchJobs };
}
