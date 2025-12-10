/**
 * Ingestion Workspace Component
 * Main workspace for managing knowledge base ingestion
 */

import { useState, useTransition } from 'react';
import { useKnowledgeBases } from '../../hooks/useKnowledgeBases';
import { useIngestionJob } from '../../hooks/useIngestionJob';
import { KBList } from './KBList';
import { CreateKBWizard } from './CreateKBWizard';
import { IngestionProgress } from './IngestionProgress';
import { startIngestion } from '../../services/ingestionApi';
import { Button, LoadingSpinner } from '../common';

type View = 'list' | 'create' | 'progress';

export function IngestionWorkspace() {
  const { kbs, loading, error, refetch } = useKnowledgeBases();
  const [view, setView] = useState<View>('list');
  const [selectedKbId, setSelectedKbId] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const { job, loading: jobLoading } = useIngestionJob(
    view === 'progress' ? selectedKbId : null,
    {
      onComplete: () => {
        startTransition(async () => {
          await refetch();
        });
      },
    }
  );

  const handleCreateClick = () => {
    setView('create');
  };

  const handleCreateSuccess = (kbId: string) => {
    setSelectedKbId(kbId);
    setView('progress');
    startTransition(async () => {
      await refetch();
    });
  };

  const handleCreateCancel = () => {
    setView('list');
  };

  const handleViewProgress = (kbId: string) => {
    setSelectedKbId(kbId);
    setView('progress');
  };

  const handleStartIngestion = (kbId: string) => {
    startTransition(async () => {
      try {
        await startIngestion(kbId);
        setSelectedKbId(kbId);
        setView('progress');
        await refetch();
      } catch (error) {
        alert(`Failed to start ingestion: ${error instanceof Error ? error.message : 'Unknown error'}`);
      }
    });
  };

  const handleBackToList = () => {
    setView('list');
    setSelectedKbId(null);
    startTransition(async () => {
      await refetch();
    });
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Knowledge Base Management</h1>
            <p className="mt-1 text-sm text-gray-600">
              Create and manage knowledge bases for RAG queries
            </p>
          </div>

          {view === 'list' && (
            <Button
              variant="primary"
              onClick={handleCreateClick}
              icon={
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
              }
            >
              Create Knowledge Base
            </Button>
          )}

          {view !== 'list' && (
            <Button
              variant="ghost"
              onClick={handleBackToList}
              icon={
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              }
            >
              Back to List
            </Button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {view === 'list' && (
          <div className="max-w-6xl mx-auto">
            {loading || isPending ? (
              <div className="py-12">
                <LoadingSpinner message="Loading knowledge bases..." />
              </div>
            ) : error ? (
              <div className="bg-red-50 border border-red-200 rounded-card p-4">
                <div className="text-red-800 font-medium">Error loading knowledge bases</div>
                <div className="text-red-600 text-sm mt-1">{error.message}</div>
                <Button
                  variant="danger"
                  size="sm"
                  onClick={refetch}
                  className="mt-3"
                >
                  Retry
                </Button>
              </div>
            ) : (
              <KBList
                kbs={kbs}
                onViewProgress={handleViewProgress}
                onStartIngestion={handleStartIngestion}
                onRefresh={refetch}
              />
            )}
          </div>
        )}

        {view === 'create' && (
          <div className="max-w-4xl mx-auto">
            <CreateKBWizard
              onSuccess={handleCreateSuccess}
              onCancel={handleCreateCancel}
            />
          </div>
        )}

        {view === 'progress' && (
          <div className="max-w-4xl mx-auto">
            {jobLoading ? (
              <div className="py-12">
                <LoadingSpinner message="Loading job status..." />
              </div>
            ) : job ? (
              <IngestionProgress
                job={job}
                onStart={() => {
                  if (selectedKbId) {
                    handleStartIngestion(selectedKbId);
                  }
                }}
              />
            ) : (
              <div className="bg-blue-50 border border-blue-200 rounded-card p-4">
                <div className="text-blue-800 font-medium">KB created; ingestion not started yet.</div>
                <p className="text-blue-700 text-sm mt-1">Click Start to begin loading and processing.</p>
                <div className="mt-3 flex gap-3">
                  {selectedKbId && (
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => handleStartIngestion(selectedKbId)}
                    >
                      Start Ingestion
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleBackToList}
                  >
                    Back to List
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
