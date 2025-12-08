/**
 * Ingestion Progress Component
 * Displays real-time progress for an ingestion job
 */

import { useTransition } from 'react';
import { IngestionJob } from '../../types/ingestion';
import { MetricCard } from './MetricCard';
import { Button, StatusBadge } from '../common';

interface IngestionProgressProps {
  job: IngestionJob;
  onRefresh?: () => void;
  onStart?: () => void;
}

// Align with backend phases (lowercase)
const PHASE_LABELS: Record<string, string> = {
  loading: 'Loading Documents',
  chunking: 'Chunking Content',
  embedding: 'Generating Embeddings',
  indexing: 'Building Index',
  completed: 'Completed',
  failed: 'Failed',
};

const PHASE_COLORS: Record<string, string> = {
  loading: 'bg-blue-500',
  chunking: 'bg-indigo-500',
  embedding: 'bg-purple-500',
  indexing: 'bg-pink-500',
  completed: 'bg-green-500',
  failed: 'bg-red-500',
};

const PHASE_ORDER: string[] = ['loading', 'chunking', 'embedding', 'indexing', 'completed'];

export function IngestionProgress({ job, onRefresh, onStart }: IngestionProgressProps) {
  const [isPending, startTransition] = useTransition();

  const isNotStarted = job.status === 'not_started' || job.phase === 'not_started';
  const isRunning = (job.status === 'running' || job.status === 'pending') && !isNotStarted;
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

  // Render explicit Not Started state: clear label, 0%, Start action only
  if (isNotStarted) {
    return (
      <div className="card space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">Ingestion Progress</h3>
          <StatusBadge variant={'inactive'}>NOT STARTED</StatusBadge>
        </div>

        <div className="p-3 bg-gray-50 border rounded-md text-sm text-gray-700">Ingestion has not started yet.</div>

        <div className="flex justify-end gap-3 pt-2">
          {onStart && (
            <Button variant="primary" onClick={onStart}>
              Start Ingestion
            </Button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="card space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">
          Ingestion Progress
        </h3>
        <StatusBadge variant={job.status as 'running' | 'completed' | 'failed'}>
          {job.status.toUpperCase()}
        </StatusBadge>
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
                    <div className="w-full bg-gray-200 rounded-pill h-2 overflow-hidden">
                      <div
                        className={`h-full transition-all duration-300 ${
                          phase === 'loading' ? 'bg-phase-crawling' :
                          phase === 'chunking' ? 'bg-phase-cleaning' :
                          phase === 'embedding' ? 'bg-phase-embedding' :
                          phase === 'indexing' ? 'bg-phase-indexing' :
                          'bg-accent-success'
                        }`}
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
        <div className="space-y-3 pt-4 border-t">
          <h4 className="text-sm font-semibold text-gray-700">Pipeline Metrics</h4>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {/* Crawling Phase */}
            {job.metrics.documents_crawled !== undefined && (
              <MetricCard
                label="Documents Crawled"
                value={job.metrics.documents_crawled}
                icon="📄"
                color="blue"
              />
            )}
            
            {/* Chunking Phase */}
            {job.metrics.chunks_created !== undefined && (
              <MetricCard
                label="Chunks Created"
                value={job.metrics.chunks_created}
                icon="✂️"
                color="indigo"
              />
            )}
            
            {/* Queue Status */}
            {job.metrics.chunks_queued !== undefined && (
              <MetricCard
                label="Total Queued"
                value={job.metrics.chunks_queued}
                subtext={job.metrics.chunks_pending ? `${job.metrics.chunks_pending} pending` : undefined}
                icon="📋"
                color="purple"
              />
            )}
            
            {/* Embedding Progress */}
            {job.metrics.chunks_embedded !== undefined && job.metrics.chunks_queued !== undefined && (
              <MetricCard
                label="Vectors Indexed"
                value={job.metrics.chunks_embedded}
                total={job.metrics.chunks_queued}
                progress={(job.metrics.chunks_embedded / job.metrics.chunks_queued) * 100}
                icon="🔢"
                color="pink"
              />
            )}
            
            {/* Processing Status */}
            {job.metrics.chunks_processing !== undefined && job.metrics.chunks_processing > 0 && (
              <MetricCard
                label="Processing"
                value={job.metrics.chunks_processing}
                icon="⚙️"
                color="yellow"
              />
            )}
            
            {/* Errors */}
            {job.metrics.chunks_failed !== undefined && job.metrics.chunks_failed > 0 && (
              <MetricCard
                label="Failed Chunks"
                value={job.metrics.chunks_failed}
                icon="⚠️"
                color="red"
              />
            )}
          </div>
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
    </div>
  );
}
