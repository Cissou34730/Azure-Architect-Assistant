/**
 * KB List Component
 * Displays list of all knowledge bases
 */

import { KnowledgeBase } from "../../types/ingestion";
import { KBListItem } from "./KBListItem";
import { deleteKB } from "../../services/ingestionApi";
import { useToast } from "../../hooks/useToast";
import { useKBJobs } from "../../hooks/useKBJobs";
import { KBListEmptyState } from "./KBListEmptyState";
import { LoadingSpinner } from "../common";

interface KBListProps {
  readonly kbs: readonly KnowledgeBase[];
  readonly onViewProgress: (kbId: string) => void;
  readonly onStartIngestion: (kbId: string) => void;
  readonly onRefresh: () => void;
}

export function KBList({
  kbs,
  onViewProgress,
  onStartIngestion,
  onRefresh,
}: KBListProps) {
  const { error: showError } = useToast();
  const { jobs, loading, refetch: refetchJobs } = useKBJobs(kbs);

  const handleDelete = async (kbId: string) => {
    try {
      await deleteKB(kbId);
      onRefresh();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      showError(`Failed to delete KB: ${msg}`);
    }
  };

  if (loading) {
    return (
      <div className="py-12">
        <LoadingSpinner message="Loading status..." />
      </div>
    );
  }

  if (kbs.length === 0) {
    return <KBListEmptyState />;
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
            void refetchJobs();
          }}
          className="px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-100 rounded-md flex items-center gap-2"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
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
          onRefresh={() => void refetchJobs()}
        />
      ))}
    </div>
  );
}
