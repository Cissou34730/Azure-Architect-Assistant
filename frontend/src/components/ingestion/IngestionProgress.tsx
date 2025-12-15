/**
 * Ingestion Progress Component
 * Displays real-time progress for an ingestion job
 */

/* eslint-disable */
import { IngestionJob } from '../../types/ingestion';
import { MetricCard } from './MetricCard';
import { Button, StatusBadge } from '../common';
import { pauseIngestion, resumeIngestion, cancelIngestion } from '../../services/ingestionApi';
import PhaseStatus from './PhaseStatus';

interface IngestionProgressProps {
  job: IngestionJob;
  onStart?: () => void;
  onRefresh?: () => void;
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

export function IngestionProgress({ job, onStart, onRefresh }: IngestionProgressProps) {
  const isNotStarted = job.status === 'not_started';
  const isRunning = (job.status === 'running' || job.status === 'pending') && !isNotStarted;
  const isPaused = job.status === 'paused';
  const progressPercent = Math.min(Math.max(job.progress, 0), 100);
  const metrics = job.metrics || {};
  const hasMetrics = Object.values(metrics ?? {}).some((v) => v !== undefined);
  
  // Determine which phases are completed
  const currentPhaseIndex = PHASE_ORDER.indexOf(job.phase);
  const isPhaseComplete = (phase: string) => {
    if (job.status === 'completed') return true;
    if (job.status === 'failed') return false;
    const phaseIndex = PHASE_ORDER.indexOf(phase);
    return phaseIndex < currentPhaseIndex;
  };
  const isPhaseActive = (phase: string) => phase === job.phase && isRunning;

  // Render explicit Not Started state
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
        <StatusBadge variant={isPaused ? 'paused' : job.status as 'running' | 'completed' | 'failed'}>
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
                  <div className="text-xs text-gray-500 mt-1">Completed</div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Phase Details from backend */}
      {job.phase_details && job.phase_details.length > 0 && (
        <div className="pt-4 border-t">
          <h4 className="text-sm font-semibold text-gray-700 mb-2">Phases</h4>
          <PhaseStatus phases={job.phase_details} />
        </div>
      )}

      {/* Metrics */}
      {hasMetrics && (
        <div className="space-y-3 pt-4 border-t">
          <h4 className="text-sm font-semibold text-gray-700">Pipeline Metrics</h4>
          
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {metrics.chunks_queued !== undefined && (
              <MetricCard
                label="Chunks Queued"
                value={metrics.chunks_queued}
                subtext={
                  metrics.chunks_pending
                    ? `${metrics.chunks_pending} pending`
                    : undefined
                }
                icon="[QUEUE]"
                color="purple"
              />
            )}

            {metrics.documents_crawled !== undefined && (
              <MetricCard
                label="Documents Crawled"
                value={metrics.documents_crawled}
                icon="[DOC]"
                color="blue"
              />
            )}

            {metrics.documents_cleaned !== undefined && (
              <MetricCard
                label="Documents Cleaned"
                value={metrics.documents_cleaned}
                icon="[CLEAN]"
                color="indigo"
              />
            )}
            
            {metrics.chunks_created !== undefined && (
              <MetricCard
                label="Chunks Created"
                value={metrics.chunks_created}
                icon="[CHNK]"
                color="indigo"
              />
            )}
            
            {metrics.chunks_pending !== undefined && (
              <MetricCard
                label="Pending"
                value={metrics.chunks_pending}
                icon="[PEND]"
                color="yellow"
              />
            )}

            {metrics.chunks_processing !== undefined && metrics.chunks_processing > 0 && (
              <MetricCard
                label="Processing"
                value={metrics.chunks_processing}
                icon="[PROC]"
                color="yellow"
              />
            )}
            
            {metrics.chunks_embedded !== undefined && metrics.chunks_queued !== undefined && (
              <MetricCard
                label="Vectors Indexed"
                value={metrics.chunks_embedded}
                total={metrics.chunks_queued}
                progress={
                  metrics.chunks_queued > 0
                    ? (metrics.chunks_embedded / metrics.chunks_queued) * 100
                    : 0
                }
                icon="[VEC]"
                color="pink"
              />
            )}
            
            {metrics.chunks_failed !== undefined && metrics.chunks_failed > 0 && (
              <MetricCard
                label="Failed Chunks"
                value={metrics.chunks_failed}
                icon="[ERR]"
                color="red"
              />
            )}
          </div>
        </div>
      )}

      {/* Controls */}
      <div className="flex justify-end gap-2 pt-4">
        {job.status === 'running' && (
          <>
            <Button variant="ghost" onClick={async () => { 
              try { 
                await pauseIngestion(job.kb_id); 
                onRefresh?.();
              } catch {} 
            }}>Pause</Button>
            <Button variant="danger" onClick={async () => { 
              if (confirm('Cancel current ingestion?')) { 
                try { 
                  await cancelIngestion(job.kb_id); 
                  onRefresh?.();
                } catch {} 
              } 
            }}>Cancel</Button>
          </>
        )}
        {isPaused && (
          <>
            <Button variant="success" onClick={async () => { 
              try { 
                await resumeIngestion(job.kb_id); 
                onRefresh?.();
              } catch {} 
            }}>Resume</Button>
            <Button variant="danger" onClick={async () => { 
              if (confirm('Cancel current ingestion?')) { 
                try { 
                  await cancelIngestion(job.kb_id); 
                  onRefresh?.();
                } catch {} 
              } 
            }}>Cancel</Button>
          </>
        )}
        {isNotStarted && onStart && (
          <Button variant="primary" onClick={onStart}>Start</Button>
        )}
      </div>

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
