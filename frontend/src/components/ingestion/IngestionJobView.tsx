import { IngestionJob } from "../../types/ingestion";
import { LoadingSpinner, Button } from "../common";
import { IngestionProgress } from "./IngestionProgress";

interface IngestionJobViewProps {
  readonly loading: boolean;
  readonly job: IngestionJob | null;
  readonly selectedKbId: string | null;
  readonly onStartIngestion: (id: string) => void;
  readonly onBack: () => void;
  readonly onRefetchJob: () => void;
}

export function IngestionJobView({
  loading,
  job,
  selectedKbId,
  onStartIngestion,
  onBack,
  onRefetchJob,
}: IngestionJobViewProps) {
  if (loading) {
    return (
      <div className="py-12">
        <LoadingSpinner message="Loading job status..." />
      </div>
    );
  }

  if (job !== null) {
    return (
      <IngestionProgress
        job={job}
        onStart={() => {
          if (selectedKbId !== null) {
            onStartIngestion(selectedKbId);
          }
        }}
        onRefresh={onRefetchJob}
      />
    );
  }

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-card p-4">
      <div className="text-blue-800 font-medium font-bold">
        Ingestion not started yet.
      </div>
      <div className="mt-3 flex gap-3">
        {selectedKbId !== null && (
          <Button
            variant="primary"
            size="sm"
            onClick={() => {
              onStartIngestion(selectedKbId);
            }}
          >
            Start Ingestion
          </Button>
        )}
        <Button variant="ghost" size="sm" onClick={onBack}>
          Back
        </Button>
      </div>
    </div>
  );
}
