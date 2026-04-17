import type { WorkflowStageResult } from "../../knowledge/types/api-kb";

export interface ChatStageEvent {
  readonly stage: string;
  readonly confidence: number;
}

export type ChatToolTraceStatus = "running" | "completed" | "failed";

export interface ChatToolTrace {
  readonly toolName: string;
  readonly argsPreview: string;
  readonly resultPreview: string;
  readonly citations: readonly string[];
  readonly durationMs: number;
  readonly status: ChatToolTraceStatus;
}

export interface PendingChangeSignal {
  readonly changeSetId: string;
  readonly summary: string;
  readonly patchCount: number;
}

export interface ActiveChatReview {
  readonly assistantMessageId: string;
  readonly answerPreview: string;
  readonly stageEvents: readonly ChatStageEvent[];
  readonly toolTraces: readonly ChatToolTrace[];
  readonly pendingChangeSignal?: PendingChangeSignal;
  readonly workflowResult?: WorkflowStageResult;
}
