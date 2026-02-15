import { Button } from "../common";

interface IngestionWorkspaceHeaderProps {
  readonly view: "list" | "create" | "progress";
  readonly onCreateClick: () => void;
  readonly onBackToList: () => void;
}

export function IngestionWorkspaceHeader({
  view,
  onCreateClick,
  onBackToList,
}: IngestionWorkspaceHeaderProps) {
  return (
    <div className="bg-card border-b border-border px-6 py-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">
            Knowledge Base Management
          </h1>
          <p className="mt-1 text-sm text-secondary">
            Create and manage knowledge bases for RAG queries
          </p>
        </div>

        {view === "list" && (
          <Button
            variant="primary"
            onClick={onCreateClick}
            icon={
              <svg
                className="w-5 h-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 4v16m8-8H4"
                />
              </svg>
            }
          >
            Create Knowledge Base
          </Button>
        )}

        {view !== "list" && (
          <Button
            variant="ghost"
            onClick={onBackToList}
            icon={
              <svg
                className="w-5 h-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 19l-7-7 7-7"
                />
              </svg>
            }
          >
            Back to List
          </Button>
        )}
      </div>
    </div>
  );
}

