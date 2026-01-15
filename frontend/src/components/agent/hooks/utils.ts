import { Message, ReasoningStep } from "../../../types/agent";
import { isRecord } from "../../../utils/typeGuards";

// eslint-disable-next-line @typescript-eslint/no-restricted-types
export function isReasoningStep(step: unknown): step is ReasoningStep {
  return (
    isRecord(step) &&
    typeof step.action === "string" &&
    typeof step.action_input === "string" &&
    typeof step.observation === "string"
  );
}

// eslint-disable-next-line @typescript-eslint/no-restricted-types
function extractReasoningSteps(m: Record<string, unknown>): ReasoningStep[] {
  const steps: ReasoningStep[] = [];
  const rawSteps = m.reasoningSteps ?? m.reasoning_steps;

  if (Array.isArray(rawSteps)) {
    for (const step of rawSteps) {
      if (isReasoningStep(step)) {
        steps.push(step);
      }
    }
  }
  return steps;
}

// eslint-disable-next-line @typescript-eslint/no-restricted-types
function extractContent(m: Record<string, unknown>): string {
  if (typeof m.content === "string") {
    return m.content;
  }
  if (m.content === null || m.content === undefined) {
    return "";
  }
  return JSON.stringify(m.content);
}

// eslint-disable-next-line @typescript-eslint/no-restricted-types
export function normalizeMessage(raw: unknown): Message {
  if (!isRecord(raw)) {
    return { role: "assistant", content: "(invalid message)" };
  }

  const role =
    raw.role === "user" || raw.role === "assistant" ? raw.role : "assistant";
  const content = extractContent(raw);
  const reasoningSteps = extractReasoningSteps(raw);

  return {
    role,
    content,
    ...(reasoningSteps.length > 0 ? { reasoningSteps } : {}),
  };
}
