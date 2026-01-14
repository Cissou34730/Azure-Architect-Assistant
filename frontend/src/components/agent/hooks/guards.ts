import { isRecord } from "../../../utils/typeGuards";

// helper to narrow unknown to message-like object
function isMessageLike(value: unknown): value is { role: "user" | "assistant"; content: string } {
  return isRecord(value) && typeof value.role === "string" && typeof value.content === "string";
}

export { isMessageLike };
