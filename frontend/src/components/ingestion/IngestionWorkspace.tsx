/**
 * Ingestion Workspace Component
 * Main workspace for managing knowledge base ingestion
 */

import { useState } from 'react';
import { useKnowledgeBases } from '../../hooks/useKnowledgeBases';
import { useIngestionJob } from '../../hooks/useIngestionJob';
import { KBList } from './KBList';
import { CreateKBWizard } from './CreateKBWizard';
import { IngestionProgress } from './IngestionProgress';
import { startIngestion } from '../../services/ingestionApi';

type View = 'list' | 'create' | 'progress';

export function IngestionWorkspace() {
  const { kbs, loading, error, refetch } = useKnowledgeBases();
  const [view, setView] = useState<View>('list');
  const [selectedKbId, setSelectedKbId] = useState<string | null>(null);
  const { job, loading: jobLoading } = useIngestionJob(
    view === 'progress' ? selectedKbId : null,
    {
      onComplete: () => {
        void refetch();
      },
    }
  );

  const handleCreateClick = () => {
    setView('create');
  };

  const handleCreateSuccess = (kbId: string) => {
    setSelectedKbId(kbId);
    setView('progress');
    void refetch();
  };

  const handleCreateCancel = () => {
    setView('list');
  };

  const handleViewProgress = (kbId: string) => {
    setSelectedKbId(kbId);
    setView('progress');
  };

  const handleStartIngestion = async (kbId: string) => {
    try {
      await startIngestion(kbId);
      setSelectedKbId(kbId);
      setView('progress');
      void refetch();
    } catch (error) {
      alert(`Failed to start ingestion: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const handleBackToList = () => {
    setView('list');
    setSelectedKbId(null);
    void refetch();
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
            <button
              onClick={handleCreateClick}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Create Knowledge Base
            </button>
          )}

          {view !== 'list' && (
            <button
              onClick={handleBackToList}
              className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-md flex items-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Back to List
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {view === 'list' && (
          <div className="max-w-6xl mx-auto">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
              </div>
            ) : error ? (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <div className="text-red-800 font-medium">Error loading knowledge bases</div>
                <div className="text-red-600 text-sm mt-1">{error.message}</div>
                <button
                  onClick={refetch}
                  className="mt-3 px-3 py-1.5 bg-red-600 text-white rounded-md hover:bg-red-700 text-sm"
                >
                  Retry
                </button>
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
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
              </div>
            ) : job ? (
              <IngestionProgress
                job={job}
                onCancel={() => {
                  void refetch();
                }}
                onRefresh={() => {
                  void refetch();
                }}
              />
            ) : (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <div className="text-yellow-800">No job found for this knowledge base.</div>
                <button
                  onClick={handleBackToList}
                  className="mt-3 px-3 py-1.5 bg-yellow-600 text-white rounded-md hover:bg-yellow-700 text-sm"
                >
                  Back to List
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
