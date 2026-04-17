/* eslint-disable max-lines -- Stream-state helpers stay together because each event transition builds on the same ActiveChatReview model. */
import type { WorkflowStageResult } from "../../knowledge/types/api-kb";
import type { JsonValue } from "../../../shared/lib/json";
import type {
  ActiveChatReview,
  ChatToolTrace,
  PendingChangeSignal,
} from "../types/chat-review";

interface ReviewIdentity {
  readonly assistantMessageId: string;
  readonly reviewState: ActiveChatReview | null;
}

interface StageEventInput extends ReviewIdentity {
  readonly stage: string;
  readonly confidence: number;
}

interface ToolTraceInput extends ReviewIdentity {
  readonly toolName: string;
  readonly argsPreview: string;
}

interface LegacyToolTraceInput extends ReviewIdentity {
  readonly toolName: string;
  readonly toolInput: JsonValue | undefined;
}

interface CompletedToolTraceInput extends ReviewIdentity {
  readonly toolName: string;
  readonly resultPreview: string;
  readonly citations: readonly string[];
  readonly status?: string;
}

interface CompletedReviewInput extends ReviewIdentity {
  readonly answerPreview: string;
  readonly workflowResult: WorkflowStageResult | undefined;
}

function stringifyPreview(inputValue: JsonValue | undefined): string {
  if (typeof inputValue === "string") {
    return inputValue;
  }

  if (inputValue === undefined) {
    return "";
  }

  return JSON.stringify(inputValue);
}

function getBaseReview({
  assistantMessageId,
  reviewState,
}: ReviewIdentity): ActiveChatReview {
  if (reviewState?.assistantMessageId === assistantMessageId) {
    return reviewState;
  }

  return createActiveChatReview(assistantMessageId);
}

function replaceOrAppendTrace(
  traceList: readonly ChatToolTrace[],
  nextTrace: ChatToolTrace,
): readonly ChatToolTrace[] {
  const runningTraceIndex = traceList.findLastIndex(
    (toolTrace) =>
      toolTrace.toolName === nextTrace.toolName &&
      toolTrace.status === "running",
  );

  if (runningTraceIndex === -1) {
    return [...traceList, nextTrace];
  }

  return traceList.map((toolTrace, currentIndex) =>
    currentIndex === runningTraceIndex ? nextTrace : toolTrace,
  );
}

function getToolTracesFromWorkflowResult(
  workflowResult: WorkflowStageResult | undefined,
  fallbackToolTraces: readonly ChatToolTrace[],
): readonly ChatToolTrace[] {
  if (workflowResult === undefined || workflowResult.toolCalls.length === 0) {
    return fallbackToolTraces;
  }

  return workflowResult.toolCalls.map((toolCall) => ({
    toolName: toolCall.toolName,
    argsPreview: toolCall.argsPreview,
    resultPreview: toolCall.resultPreview,
    citations: toolCall.citations,
    durationMs: toolCall.durationMs,
    status: "completed",
  }));
}

export function createActiveChatReview(
  assistantMessageId: string,
): ActiveChatReview {
  return {
    assistantMessageId,
    answerPreview: "",
    stageEvents: [],
    toolTraces: [],
  };
}

export function appendReviewText(
  reviewState: ActiveChatReview | null,
  assistantMessageId: string,
  textFragment: string,
): ActiveChatReview {
  const baseReview = getBaseReview({ assistantMessageId, reviewState });

  return {
    ...baseReview,
    answerPreview: `${baseReview.answerPreview}${textFragment}`,
  };
}

export function appendStageEvent({
  reviewState,
  assistantMessageId,
  stage,
  confidence,
}: StageEventInput): ActiveChatReview {
  const baseReview = getBaseReview({ assistantMessageId, reviewState });
  const hasStage = baseReview.stageEvents.some(
    (stageEvent) => stageEvent.stage === stage,
  );

  return {
    ...baseReview,
    stageEvents: hasStage
      ? baseReview.stageEvents
      : [...baseReview.stageEvents, { stage, confidence }],
  };
}

export function appendToolTrace({
  reviewState,
  assistantMessageId,
  toolName,
  argsPreview,
}: ToolTraceInput): ActiveChatReview {
  const baseReview = getBaseReview({ assistantMessageId, reviewState });

  return {
    ...baseReview,
    toolTraces: [
      ...baseReview.toolTraces,
      {
        toolName,
        argsPreview,
        resultPreview: "",
        citations: [],
        durationMs: 0,
        status: "running",
      },
    ],
  };
}

export function appendLegacyToolTrace({
  reviewState,
  assistantMessageId,
  toolName,
  toolInput,
}: LegacyToolTraceInput): ActiveChatReview {
  return appendToolTrace({
    reviewState,
    assistantMessageId,
    toolName,
    argsPreview: stringifyPreview(toolInput),
  });
}

export function completeToolTrace({
  reviewState,
  assistantMessageId,
  toolName,
  resultPreview,
  citations,
  status,
}: CompletedToolTraceInput): ActiveChatReview {
  const baseReview = getBaseReview({ assistantMessageId, reviewState });
  const existingArgsPreview =
    baseReview.toolTraces.findLast(
      (toolTrace) => toolTrace.toolName === toolName,
    )?.argsPreview ?? "";

  return {
    ...baseReview,
    toolTraces: replaceOrAppendTrace(baseReview.toolTraces, {
      toolName,
      argsPreview: existingArgsPreview,
      resultPreview,
      citations,
      durationMs: 0,
      status: status === "error" ? "failed" : "completed",
    }),
  };
}

export function setPendingChangeSignal(
  reviewState: ActiveChatReview | null,
  assistantMessageId: string,
  pendingChangeSignal: PendingChangeSignal,
): ActiveChatReview {
  const baseReview = getBaseReview({ assistantMessageId, reviewState });

  return {
    ...baseReview,
    pendingChangeSignal,
  };
}

export function completeActiveChatReview({
  reviewState,
  assistantMessageId,
  answerPreview,
  workflowResult,
}: CompletedReviewInput): ActiveChatReview {
  const baseReview = getBaseReview({ assistantMessageId, reviewState });
  const nextPendingChangeSignal =
    baseReview.pendingChangeSignal ??
    (workflowResult?.pendingChangeSet === undefined ||
    workflowResult.pendingChangeSet === null
      ? undefined
      : {
          changeSetId: workflowResult.pendingChangeSet.id,
          summary: workflowResult.pendingChangeSet.bundleSummary,
          patchCount: workflowResult.pendingChangeSet.artifactDrafts.length,
        });

  return {
    ...baseReview,
    answerPreview,
    workflowResult,
    pendingChangeSignal: nextPendingChangeSignal,
    toolTraces: getToolTracesFromWorkflowResult(
      workflowResult,
      baseReview.toolTraces,
    ),
  };
}
