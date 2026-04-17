export interface KbSource {
  readonly url: string;
  readonly title: string;
  readonly section: string;
  readonly score: number;
  readonly kbId?: string;
  readonly kbName?: string;
}

export interface WorkflowCitation {
  readonly title: string;
  readonly url: string;
  readonly source?: string;
}

export interface WorkflowNextStep {
  readonly stage: string;
  readonly tool: string | null;
  readonly rationale: string;
  readonly blockingQuestions: readonly string[];
}

export interface WorkflowToolCallTrace {
  readonly toolName: string;
  readonly argsPreview: string;
  readonly resultPreview: string;
  readonly citations: readonly string[];
  readonly durationMs: number;
}

export interface ClarificationQuestionPayloadItem {
  readonly id: string;
  readonly text: string;
  readonly theme: string;
  readonly whyItMatters: string;
  readonly architecturalImpact: string;
  readonly priority: number;
  readonly relatedRequirementIds: readonly string[];
}

export interface ClarificationQuestionsPayload {
  readonly type: "clarification_questions";
  readonly questions: readonly ClarificationQuestionPayloadItem[];
}

export interface ArchitectChoiceOption {
  readonly id: string;
  readonly title: string;
  readonly tradeoffs: readonly string[];
}

export interface ArchitectChoicePayload {
  readonly type: "architect_choice";
  readonly prompt: string;
  readonly options: readonly ArchitectChoiceOption[];
}

export type WorkflowStructuredPayload =
  | ClarificationQuestionsPayload
  | ArchitectChoicePayload;

export interface WorkflowStageResult {
  readonly stage: string;
  readonly summary: string;
  readonly pendingChangeSet?: PendingChangeDetail | null;
  readonly citations: readonly WorkflowCitation[];
  readonly warnings: readonly string[];
  readonly nextStep: WorkflowNextStep;
  readonly reasoningSummary: string;
  readonly toolCalls: readonly WorkflowToolCallTrace[];
  readonly structuredPayload?: WorkflowStructuredPayload;
}

export interface SendMessageResponse {
  readonly message: string;
  readonly projectState: ProjectState;
  readonly kbSources?: readonly KbSource[];
  readonly workflowResult?: WorkflowStageResult;
}

export interface Message {
  readonly id: string;
  readonly projectId: string;
  readonly role: "user" | "assistant";
  readonly content: string;
  readonly timestamp: string;
  readonly kbSources?: readonly KbSource[];
  readonly streamingState?: "streaming";
  readonly toolActivity?: readonly string[];
}

export interface KbQueryResponse {
  readonly answer: string;
  readonly sources: readonly KbSource[];
  readonly hasResults: boolean;
  readonly suggestedFollowUps?: readonly string[];
}

export interface KbHealthInfo {
  readonly kbId: string;
  readonly kbName: string;
  readonly status: string;
  readonly indexReady: boolean;
  readonly error?: string;
}

export interface KbInfo {
  readonly id: string;
  readonly name: string;
  readonly status: string;
  readonly profiles: readonly string[];
  readonly priority: number;
  readonly indexReady?: boolean;
}

export interface KbListResponse {
  readonly knowledgeBases: readonly KbInfo[];
}

export interface KbHealthResponse {
  readonly overallStatus: string;
  readonly knowledgeBases: readonly KbHealthInfo[];
}

import type { ProjectState } from "../../projects/types/api-project";
import type { PendingChangeDetail } from "../../projects/types/pending-changes";
