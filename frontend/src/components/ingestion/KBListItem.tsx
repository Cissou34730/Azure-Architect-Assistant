/**
 * KB List Item Component
 * Single row in the KB list
 */

import { KnowledgeBase } from '../../types/ingestion';
import { IngestionJob } from '../../types/ingestion';
import { useState } from 'react';

interface KBListItemProps {
  kb: KnowledgeBase;
  job?: IngestionJob | null;
  onViewProgress: (kbId: string) => void;
  onStartIngestion: (kbId: string) => void;
  onDelete: (kbId: string) => void;
  onCancel: (kbId: string) => void;
  onPause: (kbId: string) => void;
  onResume: (kbId: string) => void;
}

export function KBListItem({ kb, job, onViewProgress, onStartIngestion, onDelete, onCancel, onPause, onResume }: KBListItemProps) {
  const [showActions, setShowActions] = useState(false);
  const isIngesting = job?.status === 'running' || job?.status === 'pending';
  const isPaused = job?.status === 'paused';

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h3 className="text-lg font-semibold text-gray-900">{kb.name}</h3>
            <span className={`px-2 py-1 rounded-full text-xs font-medium ${
              kb.status === 'active' ? 'bg-green-100 text-green-800' :
              'bg-gray-100 text-gray-800'
            }`}>
              {kb.status}
            </span>
            {kb.indexed && (
              <span className="px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                Indexed
              </span>
            )}
          </div>

          {kb.description && (
            <p className="mt-1 text-sm text-gray-600">{kb.description}</p>
          )}

          <div className="mt-2 flex items-center gap-4 text-xs text-gray-500">
            <span>ID: {kb.id}</span>
            {kb.source_type && (
              <span>Source: {kb.source_type.replace('_', ' ')}</span>
            )}
            <span>Priority: {kb.priority}</span>
            <span>Profiles: {kb.profiles.join(', ')}</span>
          </div>

          {kb.last_indexed_at && (
            <div className="mt-1 text-xs text-gray-500">
              Last indexed: {new Date(kb.last_indexed_at).toLocaleString()}
            </div>
          )}

          {/* Job Status */}
          {job && (
            <div className="mt-3 space-y-2">
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${
                  job.status === 'running' ? 'bg-blue-500 animate-pulse' :
                  job.status === 'paused' ? 'bg-yellow-500' :
                  job.status === 'completed' ? 'bg-green-500' :
                  job.status === 'failed' ? 'bg-red-500' :
                  'bg-gray-500'
                }`} />
                <span className="text-sm font-medium text-gray-700">
                  {job.status === 'paused' ? 'PAUSED' : `${job.phase.toUpperCase()} - ${job.progress.toFixed(0)}%`}
                </span>
                <span className="text-xs text-gray-500">
                  {job.message}
                </span>
              </div>

              {/* Inline Metrics */}
              {job.metrics && Object.keys(job.metrics).length > 0 && (
                <div className="flex items-center gap-4 text-xs">
                  {job.metrics.documents_crawled !== undefined && (
                    <div className="flex items-center gap-1">
                      <span className="text-gray-500">Docs:</span>
                      <span className="font-semibold text-gray-700">{job.metrics.documents_crawled}</span>
                    </div>
                  )}
                  {job.metrics.chunks_queued !== undefined && (
                    <div className="flex items-center gap-1">
                      <span className="text-gray-500">Chunks:</span>
                      <span className="font-semibold text-gray-700">{job.metrics.chunks_queued}</span>
                    </div>
                  )}
                  {job.metrics.chunks_embedded !== undefined && job.metrics.chunks_queued !== undefined && (
                    <div className="flex items-center gap-1">
                      <span className="text-gray-500">Indexed:</span>
                      <span className="font-semibold text-gray-700">
                        {job.metrics.chunks_embedded} / {job.metrics.chunks_queued}
                      </span>
                      <span className="text-gray-500">
                        ({((job.metrics.chunks_embedded / job.metrics.chunks_queued) * 100).toFixed(0)}%)
                      </span>
                    </div>
                  )}
                  {job.metrics.chunks_pending !== undefined && job.metrics.chunks_pending > 0 && (
                    <div className="flex items-center gap-1">
                      <span className="text-gray-500">Pending:</span>
                      <span className="font-semibold text-yellow-600">{job.metrics.chunks_pending}</span>
                    </div>
                  )}
                  {job.metrics.chunks_failed !== undefined && job.metrics.chunks_failed > 0 && (
                    <div className="flex items-center gap-1">
                      <span className="text-gray-500">Failed:</span>
                      <span className="font-semibold text-red-600">{job.metrics.chunks_failed}</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-2 ml-4 relative">
          {isPaused ? (
            <>
              <button
                onClick={() => onResume(kb.id)}
                className="px-3 py-1.5 text-sm bg-green-600 text-white rounded-md hover:bg-green-700"
                title="Resume ingestion"
              >
                Resume
              </button>
              <button
                onClick={() => onCancel(kb.id)}
                className="px-3 py-1.5 text-sm bg-red-600 text-white rounded-md hover:bg-red-700"
                title="Cancel ingestion"
              >
                Cancel
              </button>
            </>
          ) : isIngesting ? (
            <>
              <button
                onClick={() => onViewProgress(kb.id)}
                className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                View Progress
              </button>
              <button
                onClick={() => onPause(kb.id)}
                className="px-3 py-1.5 text-sm bg-yellow-600 text-white rounded-md hover:bg-yellow-700"
                title="Pause ingestion"
              >
                Pause
              </button>
              <button
                onClick={() => onCancel(kb.id)}
                className="px-3 py-1.5 text-sm bg-red-600 text-white rounded-md hover:bg-red-700"
                title="Cancel ingestion"
              >
                Cancel
              </button>
            </>
          ) : (
            <button
              onClick={() => onStartIngestion(kb.id)}
              className="px-3 py-1.5 text-sm bg-green-600 text-white rounded-md hover:bg-green-700"
            >
              Start Ingestion
            </button>
          )}
          
          {/* More Actions Menu */}
          <div className="relative">
            <button
              onClick={() => setShowActions(!showActions)}
              className="px-2 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-md"
              title="More actions"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
              </svg>
            </button>
            
            {showActions && (
              <>
                <div
                  className="fixed inset-0 z-10"
                  onClick={() => setShowActions(false)}
                />
                <div className="absolute right-0 mt-1 w-48 bg-white rounded-md shadow-lg border border-gray-200 z-20">
                  <button
                    onClick={() => {
                      setShowActions(false);
                      if (window.confirm(`Are you sure you want to delete "${kb.name}"?\n\nThis will:\n- Cancel any running jobs\n- Delete all indexed data\n- Remove the knowledge base\n\nThis action cannot be undone.`)) {
                        onDelete(kb.id);
                      }
                    }}
                    className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 rounded-md"
                  >
                    Delete Knowledge Base
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
