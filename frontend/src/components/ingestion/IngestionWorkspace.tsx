/**
 * Ingestion Workspace Component
 * Main workspace for managing knowledge base ingestion
 */

import { useState, useTransition } from "react";
import { useKnowledgeBases } from "../../hooks/useKnowledgeBases";
import { useIngestionJob } from "../../hooks/useIngestionJob";
import { CreateKBWizard } from "./CreateKBWizard";
import { startIngestion } from "../../services/ingestionApi";
import { useToast } from "../../hooks/useToast";
import { IngestionWorkspaceHeader } from "./IngestionWorkspaceHeader";
import { IngestionListView } from "./IngestionListView";
import { IngestionJobView } from "./IngestionJobView";

type View = "list" | "create" | "progress";

export function IngestionWorkspace() {
  const { error: showError } = useToast();
  const { kbs, loading, error, refetch } = useKnowledgeBases();
  const [view, setView] = useState<View>("list");
  const [selectedKbId, setSelectedKbId] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const {
    job,
    loading: jobLoading,
    refetch: refetchJob,
  } = useIngestionJob(view === "progress" ? selectedKbId : null, {
    onComplete: () => {
      startTransition(async () => {
        await refetch();
      });
    },
  });

  const handleCreateSuccess = (kbId: string) => {
    setSelectedKbId(kbId);
    setView("progress");
    startTransition(async () => {
      await refetch();
    });
  };

  const handleStartIngestion = (kbId: string) => {
    startTransition(async () => {
      try {
        await startIngestion(kbId);
        setSelectedKbId(kbId);
        setView("progress");
        await refetch();
      } catch (err) {
        showError(
          `Failed to start: ${err instanceof Error ? err.message : "Unknown error"}`
        );
      }
    });
  };

  const handleBackToList = () => {
    setView("list");
    setSelectedKbId(null);
    startTransition(async () => {
      await refetch();
    });
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-gray-50">
      <IngestionWorkspaceHeader
        view={view}
        onCreateClick={() => {
          setView("create");
        }}
        onBackToList={handleBackToList}
      />

      <div className="flex-1 overflow-y-auto p-6">
        {view === "list" && (
          <div className="max-w-6xl mx-auto">
            <IngestionListView
              loading={loading}
              isPending={isPending}
              error={error}
              kbs={kbs}
              onViewProgress={(id) => {
                setSelectedKbId(id);
                setView("progress");
              }}
              onStartIngestion={handleStartIngestion}
              onRefetch={refetch}
            />
          </div>
        )}

        {view === "create" && (
          <div className="max-w-4xl mx-auto">
            <CreateKBWizard
              onSuccess={handleCreateSuccess}
              onCancel={() => {
                setView("list");
              }}
            />
          </div>
        )}

        {view === "progress" && (
          <div className="max-w-4xl mx-auto">
            <IngestionJobView
              loading={jobLoading}
              job={job}
              selectedKbId={selectedKbId}
              onStartIngestion={handleStartIngestion}
              onBack={handleBackToList}
              onRefetchJob={refetchJob}
            />
          </div>
        )}
      </div>
    </div>
  );
}
