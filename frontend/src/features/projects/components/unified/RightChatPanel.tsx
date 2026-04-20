import { useState, useEffect } from "react";
import { ChevronDown, ChevronRight, ChevronRight as ChevronRightIcon, MessageCircle, GitBranch } from "lucide-react";
import { Badge } from "../../../../shared/ui";
import { CenterChatArea } from "./CenterChatArea";
import { ChatReviewPanel } from "./ChatReviewPanel";
import { useProjectChatContext } from "../../context/useProjectChatContext";
import { useProjectStateContext } from "../../context/useProjectStateContext";

interface RightChatPanelProps {
  readonly onToggle: () => void;
}

export function RightChatPanel({ onToggle }: RightChatPanelProps) {
  const {
    activeReview,
    sendMessage,
    refreshMessages,
  } = useProjectChatContext();
  const { projectState, refreshState } = useProjectStateContext();

  const hasPendingChanges = activeReview?.pendingChangeSignal !== undefined;
  const hasClarifications =
    activeReview?.workflowResult?.structuredPayload?.type === "clarification_questions";

  const [isReviewExpanded, setIsReviewExpanded] = useState(false);

  // Auto-expand when there are pending actions
  useEffect(() => {
    if (hasPendingChanges || hasClarifications) {
      setIsReviewExpanded(true);
    }
  }, [hasPendingChanges, hasClarifications]);

  const hasReview = projectState !== null && activeReview !== null;

  return (
    <div className="flex flex-col h-full bg-card">
      <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-card shrink-0">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-brand-soft flex items-center justify-center">
            <MessageCircle className="h-4 w-4 text-brand" />
          </div>
          <div>
            <p className="text-sm font-semibold text-foreground">Chatbot</p>
            <p className="text-xs text-dim">Assistant</p>
          </div>
        </div>
        <button
          onClick={onToggle}
          className="p-1 hover:bg-muted rounded transition-colors"
          title="Hide chat panel"
          type="button"
        >
          <ChevronRightIcon className="h-5 w-5 text-secondary" />
        </button>
      </div>

      {hasReview && (
        <div className="border-b border-border shrink-0">
          <button
            type="button"
            onClick={() => { setIsReviewExpanded((prev) => !prev); }}
            className="w-full flex items-center gap-2 px-4 py-2 text-sm hover:bg-surface transition-colors"
          >
            {isReviewExpanded ? (
              <ChevronDown className="h-4 w-4 text-dim shrink-0" />
            ) : (
              <ChevronRight className="h-4 w-4 text-dim shrink-0" />
            )}
            <GitBranch className="h-4 w-4 text-brand shrink-0" />
            <span className="font-medium text-foreground">Workflow Review</span>
            <span className="flex-1" />
            {hasPendingChanges && (
              <Badge variant="warning" size="sm">
                {activeReview.pendingChangeSignal?.patchCount ?? 0} pending
              </Badge>
            )}
            {hasClarifications && (
              <Badge variant="info" size="sm">
                clarifications
              </Badge>
            )}
          </button>
          {isReviewExpanded && (
            <div className="max-h-[50%] overflow-auto">
              <ChatReviewPanel
                projectId={projectState.projectId}
                activeReview={activeReview}
                onSendMessage={sendMessage}
                onRefreshMessages={refreshMessages}
                onRefreshProjectState={refreshState}
              />
            </div>
          )}
        </div>
      )}

      <div className="flex-1 overflow-hidden">
        <CenterChatArea />
      </div>
    </div>
  );
}

