import { useMemo, useState } from "react";
import { ChevronDown, ChevronUp, FileSearch, GitBranch } from "lucide-react";
import { Badge, Button } from "../../../../shared/ui";
import type { SendMessageResponse, WorkflowCitation } from "../../../knowledge/types/api-kb";
import type { ActiveChatReview } from "../../types/chat-review";
import { usePendingChangeReview } from "../../hooks/usePendingChangeReview";
import {
  buildClarificationMessage,
  ClarificationReviewForm,
  getStageRailItems,
  getWorkflowStageLabel,
  PendingChangeReviewSection,
  StageProgressRail,
  ToolTraceSection,
} from "./ChatReviewPanelSections";

interface ChatReviewPanelProps {
  readonly projectId: string;
  readonly activeReview: ActiveChatReview | null;
  readonly onSendMessage: (
    content: string,
  ) => Promise<SendMessageResponse | undefined>;
  readonly onRefreshProjectState: () => Promise<void>;
  readonly onRefreshMessages: () => Promise<void>;
}

// eslint-disable-next-line max-lines-per-function, complexity -- This panel only orchestrates self-contained review sections and keeps the right-rail workflow cohesive.
export function ChatReviewPanel({
  projectId,
  activeReview,
  onSendMessage,
  onRefreshProjectState,
  onRefreshMessages,
}: ChatReviewPanelProps) {
  const [clarificationAnswers, setClarificationAnswers] = useState<
    Partial<Record<string, string>>
  >({});
  const [isToolTraceVisible, setIsToolTraceVisible] = useState(false);

  const pendingChangeReview = usePendingChangeReview({
    projectId,
    pendingChangeSignalId: activeReview?.pendingChangeSignal?.changeSetId,
    onRefreshProjectState,
    onRefreshMessages,
  });

  const stageRailItems = useMemo(
    () => (activeReview === null ? [] : getStageRailItems(activeReview)),
    [activeReview],
  );
  const clarificationPayload =
    activeReview?.workflowResult?.structuredPayload?.type ===
    "clarification_questions"
      ? activeReview.workflowResult.structuredPayload
      : null;
  const workflowCitations: readonly WorkflowCitation[] =
    activeReview?.workflowResult?.citations ?? [];

  if (activeReview === null) {
    return null;
  }

  return (
    <section
      className="border-b border-border bg-surface/70 px-4 py-4"
      aria-label="Current workflow review"
    >
      <div className="space-y-4">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-soft text-brand">
                <GitBranch className="h-4 w-4" />
              </div>
              <div>
                <p className="text-sm font-semibold text-foreground">
                  Current workflow review
                </p>
                <p className="text-xs text-dim">
                  {activeReview.workflowResult?.summary ?? activeReview.answerPreview}
                </p>
              </div>
            </div>
            {stageRailItems.length > 0 && <StageProgressRail items={stageRailItems} />}
          </div>
          <Badge variant="info" size="sm">
            {getWorkflowStageLabel(activeReview)}
          </Badge>
        </div>

        {clarificationPayload !== null && (
          <ClarificationReviewForm
            payload={clarificationPayload}
            clarificationAnswers={clarificationAnswers}
            onAnswerChange={(questionId, answerText) => {
              setClarificationAnswers((previousAnswers) => ({
                ...previousAnswers,
                [questionId]: answerText,
              }));
            }}
            onUseAssumption={(questionId, questionText) => {
              setClarificationAnswers((previousAnswers) => ({
                ...previousAnswers,
                [questionId]: `Assumption: ${questionText}`,
              }));
            }}
            onSubmit={() =>
              onSendMessage(
                buildClarificationMessage(
                  clarificationPayload,
                  clarificationAnswers,
                ),
              )
            }
          />
        )}

        <div className="flex flex-wrap items-center gap-2">
          <Button
            type="button"
            size="sm"
            variant="secondary"
            icon={<FileSearch className="h-4 w-4" />}
            onClick={() => {
              pendingChangeReview.setIsPendingChangesVisible((previousValue) => !previousValue);
            }}
          >
            Review pending changes
          </Button>
          {pendingChangeReview.pendingChangeSummaries.length > 0 && (
            <Badge variant="warning" size="sm">
              {pendingChangeReview.pendingChangeSummaries.length} queued
            </Badge>
          )}
          <Button
            type="button"
            size="sm"
            variant="ghost"
            icon={
              isToolTraceVisible ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )
            }
            onClick={() => {
              setIsToolTraceVisible((previousValue) => !previousValue);
            }}
          >
            Tool trace
          </Button>
          {activeReview.pendingChangeSignal !== undefined && (
            <Badge variant="warning" size="sm">
              {activeReview.pendingChangeSignal.patchCount} pending update
              {activeReview.pendingChangeSignal.patchCount === 1 ? "" : "s"}
            </Badge>
          )}
        </div>

        <PendingChangeReviewSection
          isVisible={pendingChangeReview.isPendingChangesVisible}
          isPendingChangesLoading={pendingChangeReview.isPendingChangesLoading}
          pendingChangeSummaries={pendingChangeReview.pendingChangeSummaries}
          selectedPendingChange={pendingChangeReview.selectedPendingChange}
          reviewReason={pendingChangeReview.reviewReason}
          reviewActionInFlight={pendingChangeReview.reviewActionInFlight}
          onReviewReasonChange={pendingChangeReview.setReviewReason}
          onApprove={pendingChangeReview.approvePendingChange}
          onReject={pendingChangeReview.rejectPendingChange}
        />

        <ToolTraceSection
          isVisible={isToolTraceVisible}
          activeReview={activeReview}
          workflowCitations={workflowCitations}
        />
      </div>
    </section>
  );
}
