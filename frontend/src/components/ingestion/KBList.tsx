/**
 * KB List Component
 * Displays list of all knowledge bases
 */

import { useEffect, useState } from 'react';
import { KnowledgeBase, IngestionJob, KBStatusSimple, KBIngestionDetails } from '../../types/ingestion';
import { KBListItem } from './KBListItem';
import { getKBReadyStatus, getKBIngestionDetails, deleteKB } from '../../services/ingestionApi';

interface KBListProps {
  kbs: KnowledgeBase[];
  onViewProgress: (kbId: string) => void;
  onStartIngestion: (kbId: string) => void;
  onRefresh: () => void;
}

export function KBList({ kbs, onViewProgress, onStartIngestion, onRefresh }: KBListProps) {
  const [jobs, setJobs] = useState<Map<string, IngestionJob>>(new Map());
  const [loading, setLoading] = useState(true);

  function composeJob(kbId: string, status: KBStatusSimple, details?: KBIngestionDetails): IngestionJob {
    const metrics = status.metrics || {};
    if (status.status === 'not_ready') {
      return {
        job_id: `${kbId}-job`,
        kb_id: kbId,
        status: 'not_started',
        phase: 'loading',
        progress: 0,
        message: 'Waiting to start',
        error: null,
        metrics: {
          chunks_pending: metrics.pending || 0,
          chunks_processing: metrics.processing || 0,
          chunks_embedded: metrics.done || 0,
          chunks_failed: metrics.error || 0,
          chunks_queued: (metrics.pending || 0) + (metrics.processing || 0) + (metrics.done || 0) + (metrics.error || 0),
        },
        started_at: new Date().toISOString(),
        completed_at: null,
        phase_details: details?.phase_details,
      };
    }
    if (status.status === 'ready') {
      return {
        job_id: `${kbId}-job`,
        kb_id: kbId,
        status: 'completed',
        phase: 'completed',
        progress: 100,
        message: 'Completed',
        error: null,
        metrics: {
          chunks_pending: metrics.pending || 0,
          chunks_processing: metrics.processing || 0,
          chunks_embedded: metrics.done || 0,
          chunks_failed: metrics.error || 0,
          chunks_queued: (metrics.pending || 0) + (metrics.processing || 0) + (metrics.done || 0) + (metrics.error || 0),
        },
        started_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
        phase_details: details?.phase_details,
      };
    }
    // pending
    return {
      job_id: `${kbId}-job`,
      kb_id: kbId,
      status: 'pending',
      phase: (details?.current_phase || 'loading'),
      progress: details?.overall_progress ?? 0,
      message: 'Ingestion in progress',
      error: null,
      metrics: {
        chunks_pending: metrics.pending || 0,
        chunks_processing: metrics.processing || 0,
        chunks_embedded: metrics.done || 0,
        chunks_failed: metrics.error || 0,
        chunks_queued: (metrics.pending || 0) + (metrics.processing || 0) + (metrics.done || 0) + (metrics.error || 0),
      },
      started_at: new Date().toISOString(),
      completed_at: null,
      phase_details: details?.phase_details,
    };
  }

  const fetchJobs = async () => {
    try {
      const jobsMap = new Map<string, IngestionJob>();
      for (const kb of kbs) {
        try {
          const s = await getKBReadyStatus(kb.id);
          let details: KBIngestionDetails | undefined;
          if (s.status === 'pending') {
            details = await getKBIngestionDetails(kb.id);
          }
          jobsMap.set(kb.id, composeJob(kb.id, s, details));
        } catch (e) {
          // No status yet for this KB; ignore
        }
      }
      setJobs(jobsMap);
    } catch (error) {
      console.error('Failed to fetch KB statuses:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchJobs();

    // Refresh jobs every 5 seconds
    const interval = setInterval(() => void fetchJobs(), 5000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleDelete = async (kbId: string) => {
    try {
      await deleteKB(kbId);
      onRefresh();
    } catch (error) {
      console.error('Failed to delete KB:', error);
      const errorMsg = error instanceof Error ? error.message : 'Unknown error';
      
      // Provide helpful message for permission errors
      if (errorMsg.includes('Access is denied') || errorMsg.includes('in use')) {
        alert(
          `Failed to delete KB: Files are currently in use.\n\n` +
          `Please try:\n` +
          `1. Wait a few seconds and try again\n` +
          `2. Restart the backend server if the issue persists\n\n` +
          `Technical details: ${errorMsg}`
        );
      } else {
        alert(`Failed to delete KB: ${errorMsg}`);
      }
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (kbs.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-gray-400 mb-4">
          <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">No Knowledge Bases</h3>
        <p className="text-sm text-gray-500">Create your first knowledge base to get started.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">
          Knowledge Bases ({kbs.length})
        </h2>
        <button
          onClick={onRefresh}
          className="px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-100 rounded-md flex items-center gap-2"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh
        </button>
      </div>

      {kbs.map(kb => (
        <KBListItem
          key={kb.id}
          kb={kb}
          job={jobs.get(kb.id)}
          onViewProgress={onViewProgress}
          onStartIngestion={onStartIngestion}
          onDelete={handleDelete}
        />
      ))}
    </div>
  );
}
