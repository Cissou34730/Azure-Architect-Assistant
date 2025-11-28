/**
 * Ingestion Progress Component
 * Displays real-time progress for an ingestion job
 */

import React from 'react';
import { IngestionJob } from '../../types/ingestion';
import { cancelJob, pauseJob, resumeJob } from '../../services/ingestionApi';

interface IngestionProgressProps {
  job: IngestionJob;
  onCancel?: () => void;
  onRefresh?: () => void;
}

// Align with backend phases (lowercase)
const PHASE_LABELS: Record<string, string> = {
  crawling: 'Crawling Documents',
  cleaning: 'Cleaning Content',
  embedding: 'Generating Embeddings',
  indexing: 'Building Index',
  completed: 'Completed',
  failed: 'Failed',
};

const PHASE_COLORS: Record<string, string> = {
  crawling: 'bg-blue-500',
  cleaning: 'bg-indigo-500',
  embedding: 'bg-purple-500',
  indexing: 'bg-pink-500',
  completed: 'bg-green-500',
  failed: 'bg-red-500',
};

const PHASE_ORDER: string[] = ['crawling', 'cleaning', 'embedding', 'indexing', 'completed'];

export function IngestionProgress({ job, onCancel, onRefresh }: IngestionProgressProps) {
  const [cancelling, setCancelling] = React.useState(false);
  const [pausing, setPausing] = React.useState(false);
  const [resuming, setResuming] = React.useState(false);

  const handleCancel = async () => {
    if (!window.confirm('Are you sure you want to cancel this ingestion job?')) {
      return;
    }

    setCancelling(true);
    try {
      await cancelJob(job.kb_id);
      onCancel?.();
    } catch (error) {
      console.error('Failed to cancel job:', error);
      alert(`Failed to cancel job: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setCancelling(false);
    }
  };

  const handlePause = async () => {
    setPausing(true);
    try {
      await pauseJob(job.kb_id);
      onRefresh?.();
    } catch (error) {
      console.error('Failed to pause job:', error);
      alert(`Failed to pause job: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setPausing(false);
    }
  };

  const handleResume = async () => {
    setResuming(true);
    try {
      await resumeJob(job.kb_id);
      onRefresh?.();
    } catch (error) {
      console.error('Failed to resume job:', error);
      alert(`Failed to resume job: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setResuming(false);
    }
  };

  const isRunning = job.status === 'running' || job.status === 'pending';
  const isPaused = job.status === 'paused';
  const progressPercent = Math.min(Math.max(job.progress, 0), 100);
  
  // Determine which phases are completed
  const currentPhaseIndex = PHASE_ORDER.indexOf(job.phase);
  const isPhaseComplete = (phase: string) => {
    if (job.status === 'completed') return true;
    if (job.status === 'failed') return false;
    const phaseIndex = PHASE_ORDER.indexOf(phase);
    return phaseIndex < currentPhaseIndex;
  };
  const isPhaseActive = (phase: string) => phase === job.phase && isRunning;

  return (
    <div className="bg-white rounded-lg shadow-md p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">
          Ingestion Progress
        </h3>
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${
          job.status === 'completed' ? 'bg-green-100 text-green-800' :
          job.status === 'failed' ? 'bg-red-100 text-red-800' :
          job.status === 'cancelled' ? 'bg-gray-100 text-gray-800' :
          job.status === 'paused' ? 'bg-yellow-100 text-yellow-800' :
          'bg-blue-100 text-blue-800'
        }`}>
          {job.status.toUpperCase()}
        </span>
      </div>

      {/* Phase Timeline */}
      <div className="space-y-3">
        {PHASE_ORDER.map((phase, index) => {
          const isComplete = isPhaseComplete(phase);
          const isActive = isPhaseActive(phase);
          
          return (
            <div key={phase} className="flex items-start gap-3">
              {/* Phase Indicator */}
              <div className="flex flex-col items-center">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${
                  isComplete ? 'bg-green-500 text-white' :
                  isActive ? `${PHASE_COLORS[phase]} text-white animate-pulse` :
                  'bg-gray-200 text-gray-400'
                }`}>
                  {isComplete ? (
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  ) : (
                    <span className="text-sm font-semibold">{index + 1}</span>
                  )}
                </div>
                {index < PHASE_ORDER.length - 1 && (
                  <div className={`w-0.5 h-8 ${isComplete ? 'bg-green-500' : 'bg-gray-200'}`} />
                )}
              </div>
              
              {/* Phase Details */}
              <div className="flex-1 min-w-0 pt-1">
                <div className={`text-sm font-medium ${
                  isActive ? 'text-gray-900' : 
                  isComplete ? 'text-gray-700' : 
                  'text-gray-400'
                }`}>
                  {PHASE_LABELS[phase]}
                </div>
                
                {/* Progress bar for active phase */}
                {isActive && (
                  <div className="mt-2 space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-gray-600">{job.message}</span>
                      <span className="text-gray-500 font-medium">{progressPercent.toFixed(0)}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                      <div
                        className={`h-full transition-all duration-300 ${PHASE_COLORS[phase]}`}
                        /* Dynamic width requires inline style */
                        style={{ width: `${progressPercent}%` }}
                      />
                    </div>
                  </div>
                )}
                
                {/* Show completion checkmark */}
                {isComplete && phase !== 'completed' && (
                  <div className="text-xs text-gray-500 mt-1">✓ Complete</div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Metrics */}
      {job.metrics && Object.keys(job.metrics).length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 pt-4 border-t">
          {job.metrics.pages_crawled !== undefined && (
            <div>
              <div className="text-xs text-gray-500">Pages Crawled</div>
              <div className="text-lg font-semibold text-gray-900">
                {job.metrics.pages_crawled}
                {job.metrics.pages_total && ` / ${job.metrics.pages_total}`}
              </div>
            </div>
          )}
          {job.metrics.documents_cleaned !== undefined && (
            <div>
              <div className="text-xs text-gray-500">Documents Cleaned</div>
              <div className="text-lg font-semibold text-gray-900">
                {job.metrics.documents_cleaned}
              </div>
            </div>
          )}
          {job.metrics.chunks_created !== undefined && (
            <div>
              <div className="text-xs text-gray-500">Chunks Created</div>
              <div className="text-lg font-semibold text-gray-900">
                {job.metrics.chunks_created}
              </div>
            </div>
          )}
          {job.metrics.chunks_embedded !== undefined && (
            <div>
              <div className="text-xs text-gray-500">Chunks Embedded</div>
              <div className="text-lg font-semibold text-gray-900">
                {job.metrics.chunks_embedded}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Error Display */}
      {job.error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-md">
          <div className="text-sm font-medium text-red-800">Error</div>
          <div className="text-sm text-red-600 mt-1">{job.error}</div>
        </div>
      )}

      {/* Timestamps */}
      <div className="flex justify-between text-xs text-gray-500 pt-2 border-t">
        <div>
          Started: {new Date(job.started_at).toLocaleString()}
        </div>
        {job.completed_at && (
          <div>
            Completed: {new Date(job.completed_at).toLocaleString()}
          </div>
        )}
      </div>

      {/* Actions */}
      {(isRunning || isPaused) && (
        <div className="flex justify-end gap-3 pt-2">
          {isPaused && (
            <button
              onClick={handleResume}
              disabled={resuming}
              className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {resuming ? 'Resuming...' : 'Resume Job'}
            </button>
          )}
          {isRunning && (
            <button
              onClick={handlePause}
              disabled={pausing}
              className="px-4 py-2 bg-yellow-600 text-white rounded-md hover:bg-yellow-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {pausing ? 'Pausing...' : 'Pause Job'}
            </button>
          )}
          <button
            onClick={handleCancel}
            disabled={cancelling}
            className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            {cancelling ? 'Cancelling...' : 'Cancel Job'}
          </button>
        </div>
      )}
    </div>
  );
}
