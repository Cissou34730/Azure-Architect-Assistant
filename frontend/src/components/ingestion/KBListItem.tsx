/**
 * KB List Item Component
 * Single row in the KB list
 */

import { KnowledgeBase } from '../../types/ingestion';
import { IngestionJob } from '../../types/ingestion';

interface KBListItemProps {
  kb: KnowledgeBase;
  job?: IngestionJob | null;
  onViewProgress: (kbId: string) => void;
  onStartIngestion: (kbId: string) => void;
}

export function KBListItem({ kb, job, onViewProgress, onStartIngestion }: KBListItemProps) {
  const isIngesting = job?.status === 'RUNNING' || job?.status === 'PENDING';

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
            <div className="mt-2 flex items-center gap-2">
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${
                  job.status === 'RUNNING' ? 'bg-blue-500 animate-pulse' :
                  job.status === 'COMPLETED' ? 'bg-green-500' :
                  job.status === 'FAILED' ? 'bg-red-500' :
                  'bg-gray-500'
                }`} />
                <span className="text-sm font-medium text-gray-700">
                  {job.phase} - {job.progress.toFixed(0)}%
                </span>
              </div>
              <span className="text-xs text-gray-500">
                {job.message}
              </span>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-2 ml-4">
          {isIngesting ? (
            <button
              onClick={() => onViewProgress(kb.id)}
              className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              View Progress
            </button>
          ) : (
            <button
              onClick={() => onStartIngestion(kb.id)}
              className="px-3 py-1.5 text-sm bg-green-600 text-white rounded-md hover:bg-green-700"
            >
              Start Ingestion
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
