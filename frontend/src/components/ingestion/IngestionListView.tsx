import { KnowledgeBase } from "../../types/ingestion";
import { LoadingSpinner, Button } from "../common";
import { KBList } from "./KBList";

interface IngestionListViewProps {
  readonly loading: boolean;
  readonly isPending: boolean;
  readonly error: Error | null;
  readonly kbs: readonly KnowledgeBase[];
  readonly onViewProgress: (id: string) => void;
  readonly onStartIngestion: (id: string) => void;
  readonly onRefetch: () => Promise<void>;
}

export function IngestionListView({
  loading,
  isPending,
  error,
  kbs,
  onViewProgress,
  onStartIngestion,
  onRefetch,
}: IngestionListViewProps) {
  if (loading || isPending) {
    return (
      <div className="py-12">
        <LoadingSpinner message="Loading knowledge bases..." />
      </div>
    );
  }

  if (error !== null) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-card p-4">
        <div className="text-red-800 font-medium">Error loading KBs</div>
        <div className="text-red-600 text-sm mt-1">{error.message}</div>
        <Button
          variant="danger"
          size="sm"
          onClick={() => {
            void onRefetch();
          }}
          className="mt-3"
        >
          Retry
        </Button>
      </div>
    );
  }

  return (
    <KBList
      kbs={kbs}
      onViewProgress={onViewProgress}
      onStartIngestion={onStartIngestion}
      onRefresh={() => {
        void onRefetch();
      }}
    />
  );
}
