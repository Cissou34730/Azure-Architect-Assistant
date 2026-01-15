import { KbHealthResponse } from "../../types/api";

interface Props {
  readonly healthStatus: KbHealthResponse | null;
  readonly onRefresh: () => void;
}

export function KBHeader({ healthStatus, onRefresh }: Props) {
  return (
    <div className="mb-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-2">
        Azure Knowledge Base Query
      </h1>
      <p className="text-gray-600">
        Ask questions about Azure best practices, architecture patterns,
        frameworks, and recommendations
      </p>
      {healthStatus !== null && (
        <div className="flex items-center justify-between mt-2">
          <p className="text-sm text-gray-500">
            {healthStatus.knowledgeBases.filter((kb) => kb.indexReady).length}{" "}
            of {healthStatus.knowledgeBases.length} knowledge bases ready
          </p>
          <button
            onClick={onRefresh}
            className="text-sm text-gray-600 hover:text-gray-800"
          >
            🔄 Refresh
          </button>
        </div>
      )}
    </div>
  );
}
