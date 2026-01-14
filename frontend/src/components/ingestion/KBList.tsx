/**
 * KB List Component
 * Displays list of all knowledge bases
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { KnowledgeBase, IngestionJob } from "../../types/ingestion";
import { KBListItem } from "./KBListItem";
import { getKBJobView, deleteKB } from "../../services/ingestionApi";
import { useToast } from "../../hooks/useToast";

interface KBListProps {
  kbs: KnowledgeBase[];
  onViewProgress: (kbId: string) => void;
  onStartIngestion: (kbId: string) => void;
  onRefresh: () => void;
}

export function KBList({
  kbs,
  onViewProgress,
  onStartIngestion,
  onRefresh,
}: KBListProps) {
  const { error: showError } = useToast();
  const [jobs, setJobs] = useState<Map<string, IngestionJob>>(new Map());
  const [loading, setLoading] = useState(true);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const inFlightRef = useRef(false);

  const fetchJobs = useCallback(async () => {
    if (inFlightRef.current) {
      return false;
    }
    inFlightRef.current = true;
    try {
      const jobsMap = new Map<string, IngestionJob>();
      let hasActive = false;
      for (const kb of kbs) {
        try {
          const jobView = await getKBJobView(kb.id);
          if (jobView.status === "pending" || jobView.status === "paused") {
            hasActive = true;
          }
          jobsMap.set(kb.id, jobView);
        } catch (e) {
          // No status yet for this KB; ignore
        }
      }
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

    // clear any existing timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }

    const loop = async () => {
      if (cancelled) {
        return;
      }
      const hasActive = await fetchJobs();
      if (cancelled) {
        return;
      }
      const delay = hasActive ? 5000 : 10000;
      timeoutRef.current = setTimeout(() => void loop(), delay);
    };

    void loop();

    return () => {
      cancelled = true;
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    };
  }, [fetchJobs]);

  const handleDelete = async (kbId: string) => {
    try {
      await deleteKB(kbId);
      onRefresh();
    } catch (error) {
      console.error("Failed to delete KB:", error);
      const errorMsg = error instanceof Error ? error.message : "Unknown error";

      // Provide helpful message for permission errors
      if (
        errorMsg.includes("Access is denied") ||
        errorMsg.includes("in use")
      ) {
        showError(
          `Failed to delete KB: Files are currently in use. Please wait a few seconds and try again or restart the backend server. (${errorMsg})`,
          10000,
        );
      } else {
        showError(`Failed to delete KB: ${errorMsg}`);
      }
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (kbs.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-gray-400 mb-4">
          <svg
            className="mx-auto h-12 w-12"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          No Knowledge Bases
        </h3>
        <p className="text-sm text-gray-500">
          Create your first knowledge base to get started.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">
          Knowledge Bases ({kbs.length})
        </h2>
        <button
          onClick={() => {
            onRefresh();
            void fetchJobs();
          }}
          className="px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-100 rounded-md flex items-center gap-2"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
          Refresh
        </button>
      </div>

      {kbs.map((kb) => (
        <KBListItem
          key={kb.id}
          kb={kb}
          job={jobs.get(kb.id)}
          onViewProgress={onViewProgress}
          onStartIngestion={onStartIngestion}
          onDelete={handleDelete}
          onRefresh={fetchJobs}
        />
      ))}
    </div>
  );
}
