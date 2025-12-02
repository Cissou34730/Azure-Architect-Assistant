/**
 * KB List Item Component
 * Single row in the KB list
 */

import { KnowledgeBase } from '../../types/ingestion';
import { IngestionJob } from '../../types/ingestion';
import { useState, useRef, useEffect } from 'react';
import { Button, StatusBadge } from '../common';

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
  const dropdownRef = useRef<HTMLDivElement>(null);
  const isIngesting = job?.status === 'running' || job?.status === 'pending';
  const isPaused = job?.status === 'paused';
  const isCompleted = job?.status === 'completed';
  const canStartIngestion = !isIngesting && !isPaused && !isCompleted; // Only show Start for pending/failed/cancelled or no job
  
  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowActions(false);
      }
    };
    
    if (showActions) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
    return undefined;
  }, [showActions]);
  
  // Keyboard navigation for dropdown
  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'Escape') {
      setShowActions(false);
    }
  };
  
  // Debug: Log metrics data
  if (job && job.metrics) {
    console.log(`KB ${kb.id} metrics:`, job.metrics);
  }

  return (
    <div className="card hover:shadow-lg transition-shadow" role="article" aria-label={`Knowledge base: ${kb.name}`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h3 className="text-lg font-semibold text-gray-900">{kb.name}</h3>
            <StatusBadge variant={kb.status === 'active' ? 'active' : 'inactive'}>
              {kb.status}
            </StatusBadge>
            {kb.indexed && (
              <StatusBadge variant="active">
                Indexed
              </StatusBadge>
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
                <div className={`w-2 h-2 rounded-pill ${
                  job.status === 'running' ? 'bg-status-running animate-pulse' :
                  job.status === 'paused' ? 'bg-status-paused' :
                  job.status === 'completed' ? 'bg-status-completed' :
                  job.status === 'failed' ? 'bg-status-failed' :
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
              {job.metrics && (
                <div className="flex items-center gap-4 text-xs">
                  {job.metrics.documents_crawled !== undefined && job.metrics.documents_crawled > 0 && (
                    <div className="flex items-center gap-1">
                      <span className="text-gray-500">Docs:</span>
                      <span className="font-semibold text-gray-700">{job.metrics.documents_crawled}</span>
                    </div>
                  )}
                  {job.metrics.chunks_queued !== undefined && job.metrics.chunks_queued > 0 && (
                    <div className="flex items-center gap-1">
                      <span className="text-gray-500">Chunks:</span>
                      <span className="font-semibold text-gray-700">{job.metrics.chunks_queued}</span>
                    </div>
                  )}
                  {job.metrics.chunks_embedded !== undefined && job.metrics.chunks_embedded > 0 && (
                    <div className="flex items-center gap-1">
                      <span className="text-gray-500">Indexed:</span>
                      <span className="font-semibold text-gray-700">
                        {job.metrics.chunks_embedded}
                        {job.metrics.chunks_queued && job.metrics.chunks_queued > 0 && (
                          <>
                            {' / '}
                            {job.metrics.chunks_queued}
                            <span className="text-gray-500 ml-1">
                              ({((job.metrics.chunks_embedded / job.metrics.chunks_queued) * 100).toFixed(0)}%)
                            </span>
                          </>
                        )}
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
        <div className="flex gap-2 ml-4">
          {isPaused ? (
            <>
              <Button
                variant="success"
                size="sm"
                onClick={() => onResume(kb.id)}
                aria-label="Resume ingestion"
              >
                Resume
              </Button>
              <Button
                variant="danger"
                size="sm"
                onClick={() => onCancel(kb.id)}
                aria-label="Cancel ingestion"
              >
                Cancel
              </Button>
            </>
          ) : isIngesting ? (
            <>
              <Button
                variant="primary"
                size="sm"
                onClick={() => onViewProgress(kb.id)}
              >
                View Progress
              </Button>
              <Button
                variant="warning"
                size="sm"
                onClick={() => onPause(kb.id)}
                aria-label="Pause ingestion"
              >
                Pause
              </Button>
              <Button
                variant="danger"
                size="sm"
                onClick={() => onCancel(kb.id)}
                aria-label="Cancel ingestion"
              >
                Cancel
              </Button>
            </>
          ) : canStartIngestion ? (
            <Button
              variant="success"
              size="sm"
              onClick={() => onStartIngestion(kb.id)}
            >
              Start Ingestion
            </Button>
          ) : null}
          
          {/* More Actions Menu */}
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setShowActions(!showActions)}
              onKeyDown={handleKeyDown}
              className="px-2 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-button"
              aria-label="More actions"
              aria-expanded={showActions ? 'true' : 'false'}
              aria-haspopup="menu"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
              </svg>
            </button>
            
            {showActions && (
              <div 
                className="absolute right-0 mt-1 w-48 bg-white rounded-button shadow-lg border border-gray-200 z-20"
                role="menu"
                aria-orientation="vertical"
              >
                <button
                  onClick={() => {
                    setShowActions(false);
                    if (window.confirm(`Are you sure you want to delete "${kb.name}"?\n\nThis will:\n- Cancel any running jobs\n- Delete all indexed data\n- Remove the knowledge base\n\nThis action cannot be undone.`)) {
                      onDelete(kb.id);
                    }
                  }}
                  className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 rounded-button"
                  role="menuitem"
                >
                  Delete Knowledge Base
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
