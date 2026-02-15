import { KbHealthResponse } from "../../types/api";

interface Props {
  readonly healthStatus: KbHealthResponse | null;
  readonly onRefresh: () => void;
}

export function KBHeader({ healthStatus, onRefresh }: Props) {
  return (
    <div className="mb-8">
      <h1 className="text-3xl font-bold text-foreground mb-2">
        Azure Knowledge Base Query
      </h1>
      <p className="text-secondary">
        Ask questions about Azure best practices, architecture patterns,
        frameworks, and recommendations
      </p>
      {healthStatus !== null && (
        <div className="flex items-center justify-between mt-2">
          <p className="text-sm text-dim">
            {healthStatus.knowledgeBases.filter((kb) => kb.indexReady).length}{" "}
            of {healthStatus.knowledgeBases.length} knowledge bases ready
          </p>
          <button
            onClick={onRefresh}
            className="text-sm text-secondary hover:text-foreground"
          >
            🔄 Refresh
          </button>
        </div>
      )}
    </div>
  );
}

