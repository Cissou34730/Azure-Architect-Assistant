/* eslint-disable max-lines -- Review UI sections stay co-located so the typed chat-review surface can evolve together without cross-file prop churn. */
import { Check, Link2 } from "lucide-react";
import { Badge, Button } from "../../../../shared/ui";
import type { ActiveChatReview } from "../../types/chat-review";
import type {
  PendingChangeDetail,
  PendingChangeSummary,
} from "../../types/pending-changes";
import type {
  ClarificationQuestionPayloadItem,
  ClarificationQuestionsPayload,
  SendMessageResponse,
  WorkflowCitation,
} from "../../../knowledge/types/api-kb";

interface ReviewActionState {
  readonly reviewReason: string;
  readonly reviewActionInFlight: "approve" | "reject" | null;
}

interface PendingChangeReviewSectionProps extends ReviewActionState {
  readonly isVisible: boolean;
  readonly isPendingChangesLoading: boolean;
  readonly pendingChangeSummaries: readonly PendingChangeSummary[];
  readonly selectedPendingChange: PendingChangeDetail | null;
  readonly onReviewReasonChange: (reviewReason: string) => void;
  readonly onApprove: () => Promise<void>;
  readonly onReject: () => Promise<void>;
}

interface ClarificationReviewFormProps {
  readonly payload: ClarificationQuestionsPayload;
  readonly clarificationAnswers: Partial<Record<string, string>>;
  readonly onAnswerChange: (questionId: string, answerText: string) => void;
  readonly onUseAssumption: (questionId: string, questionText: string) => void;
  readonly onSubmit: () => Promise<SendMessageResponse | undefined>;
}

interface ToolTraceSectionProps {
  readonly isVisible: boolean;
  readonly activeReview: ActiveChatReview;
  readonly workflowCitations: readonly WorkflowCitation[];
}

interface StageRailItem {
  readonly id: string;
  readonly label: string;
}

const STAGE_LABELS: Readonly<Partial<Record<string, string>>> = {
  clarify: "Clarify",
  propose_candidate: "Architecture",
  manage_adr: "ADR",
  extract_requirements: "Requirements",
  review: "Review",
  done: "Done",
};

function getStageLabel(stageName: string): string {
  const mappedLabel = STAGE_LABELS[stageName];
  if (mappedLabel !== undefined) {
    return mappedLabel;
  }

  return stageName
    .split(/[_\s-]+/)
    .filter((stageWord) => stageWord !== "")
    .map((stageWord) => stageWord.charAt(0).toUpperCase() + stageWord.slice(1))
    .join(" ");
}

function getGroupedClarificationQuestions(
  payload: ClarificationQuestionsPayload,
): Readonly<Record<string, readonly ClarificationQuestionPayloadItem[]>> {
  return payload.questions.reduce<Record<string, readonly ClarificationQuestionPayloadItem[]>>(
    (questionGroupMap, clarificationQuestion) => ({
      ...questionGroupMap,
      [clarificationQuestion.theme]: [
        ...(questionGroupMap[clarificationQuestion.theme] ?? []),
        clarificationQuestion,
      ],
    }),
    {},
  );
}

function getArtifactDraftTitle(pendingChangeDetail: PendingChangeDetail): string {
  const firstArtifactDraft = pendingChangeDetail.artifactDrafts.at(0);
  if (firstArtifactDraft === undefined) {
    return pendingChangeDetail.bundleSummary;
  }

  const titleValue = firstArtifactDraft.content.title;
  return typeof titleValue === "string" && titleValue !== ""
    ? titleValue
    : pendingChangeDetail.bundleSummary;
}

function toCompletedToolTrace(
  toolCall: NonNullable<ActiveChatReview["workflowResult"]>["toolCalls"][number],
): ActiveChatReview["toolTraces"][number] {
  return {
    toolName: toolCall.toolName,
    argsPreview: toolCall.argsPreview,
    resultPreview: toolCall.resultPreview,
    citations: toolCall.citations,
    durationMs: toolCall.durationMs,
    status: "completed",
  };
}

export function getStageRailItems(activeReview: ActiveChatReview): readonly StageRailItem[] {
  const reviewStageNames = activeReview.stageEvents.map((stageEvent) => stageEvent.stage);
  const workflowStageName = activeReview.workflowResult?.stage;
  const stageNames = workflowStageName === undefined
    ? reviewStageNames
    : [...reviewStageNames, workflowStageName];

  return [...new Set(stageNames)].map((stageName) => ({
    id: stageName,
    label: getStageLabel(stageName),
  }));
}

export function getWorkflowStageLabel(activeReview: ActiveChatReview): string {
  return getStageLabel(activeReview.workflowResult?.stage ?? "review");
}

export function buildClarificationMessage(
  payload: ClarificationQuestionsPayload,
  clarificationAnswers: Partial<Record<string, string>>,
): string {
  const answerLines = payload.questions.map((clarificationQuestion) => {
    const answerText = clarificationAnswers[clarificationQuestion.id]?.trim() ?? "";
    return `- [${clarificationQuestion.id}] ${clarificationQuestion.text}\n  Answer: ${answerText}`;
  });

  return ["Clarification answers:", ...answerLines].join("\n");
}

export function StageProgressRail({ items }: { readonly items: readonly StageRailItem[] }) {
  return (
    <div className="flex flex-wrap items-center gap-2" aria-label="Workflow stage rail">
      {items.map((stageRailItem, index) => (
        <div key={stageRailItem.id} className="flex items-center gap-2">
          <div className="flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1 text-xs font-semibold text-secondary">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-brand-soft text-brand">
              <Check className="h-3 w-3" />
            </span>
            <span>{stageRailItem.label}</span>
          </div>
          {index < items.length - 1 && <div className="h-px w-4 bg-border" />}
        </div>
      ))}
    </div>
  );
}

export function ClarificationReviewForm({
  payload,
  clarificationAnswers,
  onAnswerChange,
  onUseAssumption,
  onSubmit,
}: ClarificationReviewFormProps) {
  const groupedClarificationQuestions = getGroupedClarificationQuestions(payload);
  const canSubmit = payload.questions.every((clarificationQuestion) => {
    const answerText = clarificationAnswers[clarificationQuestion.id]?.trim() ?? "";
    return answerText !== "";
  });

  return (
    <form
      className="space-y-4 rounded-xl border border-border bg-card p-4"
      onSubmit={(event) => {
        event.preventDefault();
        void onSubmit();
      }}
    >
      <div className="space-y-1">
        <p className="text-sm font-semibold text-foreground">Clarification questions</p>
        <p className="text-xs text-dim">
          Capture the missing answers here and send them through the existing chat flow.
        </p>
      </div>

      {Object.entries(groupedClarificationQuestions).map(
        ([questionTheme, clarificationQuestions]) => (
          <div key={questionTheme} className="space-y-3">
            <Badge variant="primary" size="sm">
              {questionTheme}
            </Badge>
            {clarificationQuestions.map((clarificationQuestion) => (
              <div
                key={clarificationQuestion.id}
                className="space-y-2 rounded-lg border border-border bg-surface p-3"
              >
                <label
                  className="block text-sm font-medium text-foreground"
                  htmlFor={clarificationQuestion.id}
                >
                  {clarificationQuestion.text}
                </label>
                <p className="text-xs text-dim">{clarificationQuestion.whyItMatters}</p>
                <textarea
                  id={clarificationQuestion.id}
                  className="min-h-20 w-full rounded-lg border border-border-stronger bg-card px-3 py-2 text-sm text-foreground outline-none focus:border-brand focus:ring-2 focus:ring-brand/20"
                  value={clarificationAnswers[clarificationQuestion.id] ?? ""}
                  onChange={(event) => {
                    onAnswerChange(clarificationQuestion.id, event.target.value);
                  }}
                />
                <button
                  type="button"
                  className="text-xs font-medium text-brand hover:text-brand-strong"
                  onClick={() => {
                    onUseAssumption(
                      clarificationQuestion.id,
                      clarificationQuestion.text,
                    );
                  }}
                >
                  Use assumption
                </button>
              </div>
            ))}
          </div>
        ),
      )}

      <Button type="submit" size="sm" disabled={!canSubmit}>
        Send clarification answers
      </Button>
    </form>
  );
}

// eslint-disable-next-line max-lines-per-function -- Pending-change review keeps its summary, draft list, and review actions together for faster triage.
export function PendingChangeReviewSection({
  isVisible,
  isPendingChangesLoading,
  pendingChangeSummaries,
  selectedPendingChange,
  reviewReason,
  reviewActionInFlight,
  onReviewReasonChange,
  onApprove,
  onReject,
}: PendingChangeReviewSectionProps) {
  if (!isVisible) {
    return null;
  }

  return (
    <div className="space-y-3 rounded-xl border border-border bg-card p-4">
      <div className="space-y-1">
        <p className="text-sm font-semibold text-foreground">Pending changes</p>
        <p className="text-xs text-dim">
          Review the DB-backed change set before mutating canonical project state.
        </p>
      </div>

      {isPendingChangesLoading && (
        <p className="text-sm text-secondary">Loading pending changes…</p>
      )}

      {!isPendingChangesLoading && selectedPendingChange === null && (
        <p className="text-sm text-dim">
          {pendingChangeSummaries.length === 0
            ? "No pending changes are waiting for review."
            : "Select a pending change to continue the review."}
        </p>
      )}

      {selectedPendingChange !== null && (
        <div
          className="space-y-3 rounded-lg border border-border bg-surface p-3"
          data-testid={`pending-change-${selectedPendingChange.id}`}
        >
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Badge variant="warning" size="sm">
                {getStageLabel(selectedPendingChange.stage)}
              </Badge>
              <p className="text-sm font-semibold text-foreground">
                {selectedPendingChange.bundleSummary}
              </p>
            </div>
            <p className="text-xs text-dim">{getArtifactDraftTitle(selectedPendingChange)}</p>
          </div>

          <ul className="space-y-2 text-sm text-secondary">
            {selectedPendingChange.artifactDrafts.map((artifactDraft) => {
              const draftTitle = artifactDraft.content.title;
              const draftText = artifactDraft.content.text;
              return (
                <li
                  key={artifactDraft.id}
                  className="rounded-md border border-border bg-card px-3 py-2"
                >
                  <p className="font-medium text-foreground">
                    {typeof draftTitle === "string" ? draftTitle : artifactDraft.artifactType}
                  </p>
                  {typeof draftText === "string" && (
                    <p className="mt-1 text-xs text-dim">{draftText}</p>
                  )}
                </li>
              );
            })}
          </ul>

          <label
            className="block text-xs font-medium text-secondary"
            htmlFor="pending-change-review-reason"
          >
            Reject reason (optional)
          </label>
          <textarea
            id="pending-change-review-reason"
            className="min-h-20 w-full rounded-lg border border-border-stronger bg-card px-3 py-2 text-sm text-foreground outline-none focus:border-brand focus:ring-2 focus:ring-brand/20"
            value={reviewReason}
            onChange={(event) => {
              onReviewReasonChange(event.target.value);
            }}
          />

          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              size="sm"
              isLoading={reviewActionInFlight === "approve"}
              onClick={() => {
                void onApprove();
              }}
            >
              Approve
            </Button>
            <Button
              type="button"
              size="sm"
              variant="secondary"
              isLoading={reviewActionInFlight === "reject"}
              onClick={() => {
                void onReject();
              }}
            >
              Reject
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

export function ToolTraceSection({
  isVisible,
  activeReview,
  workflowCitations,
}: ToolTraceSectionProps) {
  if (!isVisible) {
    return null;
  }

  const toolTraceItems =
    activeReview.workflowResult !== undefined &&
    activeReview.workflowResult.toolCalls.length > 0
      ? activeReview.workflowResult.toolCalls.map((toolCall) =>
          toCompletedToolTrace(toolCall),
        )
      : activeReview.toolTraces;

  return (
    <div className="space-y-3 rounded-xl border border-border bg-card p-4">
      <div className="space-y-1">
        <p className="text-sm font-semibold text-foreground">Tool trace</p>
        <p className="text-xs text-dim">
          Inspect the calls and citations that informed this turn.
        </p>
      </div>

      {toolTraceItems.length === 0 ? (
        <p className="text-sm text-dim">No tool calls were recorded for this turn.</p>
      ) : (
        <ul className="space-y-3">
          {toolTraceItems.map((toolTraceItem) => (
            <li
              key={`${toolTraceItem.toolName}-${toolTraceItem.argsPreview}`}
              className="rounded-lg border border-border bg-surface p-3"
            >
              <div className="flex items-center gap-2">
                <Badge
                  variant={toolTraceItem.status === "failed" ? "error" : "info"}
                  size="sm"
                >
                  {toolTraceItem.toolName}
                </Badge>
                {toolTraceItem.durationMs > 0 && (
                  <span className="text-xs text-dim">{toolTraceItem.durationMs} ms</span>
                )}
              </div>
              {toolTraceItem.argsPreview !== "" && (
                <p className="mt-2 text-xs text-secondary">Args: {toolTraceItem.argsPreview}</p>
              )}
              {toolTraceItem.resultPreview !== "" && (
                <p className="mt-1 text-xs text-secondary">
                  Result: {toolTraceItem.resultPreview}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}

      {workflowCitations.length > 0 && (
        <div className="space-y-2 border-t border-border pt-3">
          <p className="text-sm font-semibold text-foreground">Citations</p>
          <ul className="space-y-2">
            {workflowCitations.map((workflowCitation) => (
              <li key={workflowCitation.url}>
                <a
                  className="flex items-center gap-2 text-sm text-brand hover:text-brand-strong"
                  href={workflowCitation.url}
                  rel="noreferrer"
                  target="_blank"
                >
                  <Link2 className="h-4 w-4" />
                  <span>{workflowCitation.title}</span>
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
