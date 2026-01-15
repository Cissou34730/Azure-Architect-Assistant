import type { AgentStatus } from "../../types/agent";

interface WorkspaceHeaderProps {
  readonly agentStatus: AgentStatus;
  readonly showReasoning: boolean;
  readonly onClearChat: () => void;
  readonly onToggleReasoning: () => void;
}

export function WorkspaceHeader({
  agentStatus,
  showReasoning,
  onClearChat,
  onToggleReasoning,
}: WorkspaceHeaderProps) {
  return (
    <div className="flex items-center justify-between mb-4">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">
          Azure Architect Assistant
        </h1>
        <p className="mt-1 text-gray-600">
          Chat with the ReAct agent powered by Microsoft documentation
        </p>
      </div>
      <div className="flex items-center space-x-4">
        <StatusBadge status={agentStatus} />
        <button
          onClick={onClearChat}
          className="px-4 py-2 text-sm text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors"
        >
          Clear Chat
        </button>
        <button
          onClick={onToggleReasoning}
          className={`px-4 py-2 text-sm rounded-md transition-colors ${
            showReasoning
              ? "bg-accent-primary text-white"
              : "text-gray-700 hover:bg-gray-100"
          }`}
        >
          {showReasoning ? "Hide" : "Show"} Reasoning
        </button>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { readonly status: AgentStatus }) {
  const statusConfig: Record<
    AgentStatus,
    { readonly bg: string; readonly text: string; readonly label: string }
  > = {
    healthy: { bg: "bg-green-100", text: "text-green-800", label: "● Ready" },
    // Status keys come from backend API which uses snake_case
    // eslint-disable-next-line @typescript-eslint/naming-convention
    not_initialized: {
      bg: "bg-yellow-100",
      text: "text-yellow-800",
      label: "○ Not Initialized",
    },
    unknown: { bg: "bg-gray-100", text: "text-gray-800", label: "○ Unknown" },
  };

  const config = statusConfig[status];

  return (
    <div
      className={`px-3 py-1 rounded-full text-sm font-medium ${config.bg} ${config.text}`}
    >
      {config.label}
    </div>
  );
}
