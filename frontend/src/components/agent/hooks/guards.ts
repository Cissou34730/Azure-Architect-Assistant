import { isRecord } from "../../../utils/typeGuards";
import type {
  AgentResponse,
  ProjectState,
  Project,
} from "../../../types/agent";

// helper to narrow unknown to message-like object
 
function isMessageLike(
  // eslint-disable-next-line @typescript-eslint/no-restricted-types
  value: unknown
): value is { role: "user" | "assistant"; content: string } {
  return (
    isRecord(value) &&
    (value.role === "user" || value.role === "assistant") &&
    typeof value.content === "string"
  );
}

// eslint-disable-next-line @typescript-eslint/no-restricted-types
function isAgentResponse(value: unknown): value is AgentResponse {
  return (
    isRecord(value) &&
    typeof value.answer === "string" &&
    Array.isArray(value.reasoningSteps)
  );
}

// eslint-disable-next-line @typescript-eslint/no-restricted-types
function isProjectState(value: unknown): value is ProjectState {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    isRecord(value.context) &&
    isRecord(value.nfrs) &&
    isRecord(value.structure)
  );
}

// eslint-disable-next-line @typescript-eslint/no-restricted-types
function isProject(value: unknown): value is Project {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.name === "string"
  );
}

export { isMessageLike, isAgentResponse, isProjectState, isProject };
