/* eslint-disable max-lines -- SSE stream handler; each function is minimal but the full protocol implementation requires these lines */
import type { Message, SendMessageResponse } from "../../knowledge/types/api-kb";
import { API_BASE } from "../../../shared/config/api";
import { fetchWithErrorHandling } from "../../../shared/http/fetchWithErrorHandling";

interface ReasoningStep {
  readonly action: string;
  readonly action_input: string;
  readonly observation: string;
}

interface StreamEventMap {
  readonly message_start: { readonly role: "assistant" };
  readonly token: { readonly text: string };
  readonly tool_start: {
    readonly tool: string;
    // eslint-disable-next-line @typescript-eslint/no-restricted-types -- tool_input is genuinely unknown at the API boundary
    readonly tool_input: unknown;
  };
  readonly tool_result: {
    readonly tool: string;
    readonly tool_call_id?: string;
    readonly content: string;
    readonly status?: string;
  };
  readonly final: {
    readonly answer: string;
    readonly success: boolean;
    readonly project_state?: SendMessageResponse["projectState"];
    readonly reasoning_steps: readonly ReasoningStep[];
    readonly error?: string;
  };
  readonly error: { readonly error: string };
}

type StreamEventName = keyof StreamEventMap;

interface StreamCallbacks {
  readonly onMessageStart?: (payload: StreamEventMap["message_start"]) => void;
  readonly onToken?: (payload: StreamEventMap["token"]) => void;
  readonly onToolStart?: (payload: StreamEventMap["tool_start"]) => void;
  readonly onToolResult?: (payload: StreamEventMap["tool_result"]) => void;
  readonly onFinal?: (payload: StreamEventMap["final"]) => void;
  readonly onError?: (payload: StreamEventMap["error"]) => void;
}

function toErrorMessage(response: Response, body: string): string {
  try {
    // eslint-disable-next-line @typescript-eslint/no-restricted-types -- JSON.parse result at external API boundary
    const parsed: unknown = JSON.parse(body);
    if (
      typeof parsed === "object" &&
      parsed !== null &&
      "detail" in parsed &&
      typeof parsed.detail === "string" &&
      parsed.detail !== ""
    ) {
      return parsed.detail;
    }
  } catch {
    // Ignore JSON parse issues and fall back to status/body text.
  }
  return body || `Request failed with status ${response.status}`;
}

// Dispatch table: O(1) lookup removes switch-based cyclomatic complexity
// eslint-disable-next-line @typescript-eslint/no-restricted-types -- raw API stream event payload; type is genuinely unknown before dispatch
type EventHandlerFn = (parsed: unknown, callbacks: StreamCallbacks) => StreamEventMap["final"] | null;

const EVENT_DISPATCH: Readonly<Record<StreamEventName, EventHandlerFn>> = {
  message_start(parsed, cb) {
    // eslint-disable-next-line no-restricted-syntax, @typescript-eslint/no-unsafe-type-assertion -- API boundary: payload shape guaranteed by server
    cb.onMessageStart?.(parsed as StreamEventMap["message_start"]);
    return null;
  },
  token(parsed, cb) {
    // eslint-disable-next-line no-restricted-syntax, @typescript-eslint/no-unsafe-type-assertion -- API boundary
    cb.onToken?.(parsed as StreamEventMap["token"]);
    return null;
  },
  tool_start(parsed, cb) {
    // eslint-disable-next-line no-restricted-syntax, @typescript-eslint/no-unsafe-type-assertion -- API boundary
    cb.onToolStart?.(parsed as StreamEventMap["tool_start"]);
    return null;
  },
  tool_result(parsed, cb) {
    // eslint-disable-next-line no-restricted-syntax, @typescript-eslint/no-unsafe-type-assertion -- API boundary
    cb.onToolResult?.(parsed as StreamEventMap["tool_result"]);
    return null;
  },
  error(parsed, cb) {
    // eslint-disable-next-line no-restricted-syntax, @typescript-eslint/no-unsafe-type-assertion -- API boundary
    cb.onError?.(parsed as StreamEventMap["error"]);
    return null;
  },
  final(parsed, cb) {
    // eslint-disable-next-line no-restricted-syntax, @typescript-eslint/no-unsafe-type-assertion -- API boundary
    const payload = parsed as StreamEventMap["final"];
    cb.onFinal?.(payload);
    return payload;
  },
};

function isKnownEvent(name: string): name is StreamEventName {
  return name in EVENT_DISPATCH;
}

function dispatchStreamEvent(
  eventName: string,
  data: string,
  callbacks?: StreamCallbacks,
): StreamEventMap["final"] | null {
  // eslint-disable-next-line @typescript-eslint/no-restricted-types -- raw SSE data string at API boundary
  let parsed: unknown;
  try {
    parsed = JSON.parse(data);
  } catch {
    throw new Error(`Invalid stream payload for event '${eventName}'`);
  }
  if (!isKnownEvent(eventName)) return null;
  return EVENT_DISPATCH[eventName](parsed, callbacks ?? {});
}

function consumeSseBuffer(
  buffer: string,
  callbacks?: StreamCallbacks,
): { remaining: string; finalPayload: StreamEventMap["final"] | null } {
  let remaining = buffer;
  let finalPayload: StreamEventMap["final"] | null = null;

  for (;;) {
    const boundary = remaining.indexOf("\n\n");
    if (boundary === -1) {
      return { remaining, finalPayload };
    }

    const rawEvent = remaining.slice(0, boundary);
    remaining = remaining.slice(boundary + 2);
    if (rawEvent.trim() === "") {
      continue;
    }

    let eventName = "message";
    const dataLines: string[] = [];
    for (const line of rawEvent.split(/\r?\n/)) {
      if (line.startsWith("event:")) {
        eventName = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trim());
      }
    }

    const payload = dispatchStreamEvent(eventName, dataLines.join("\n"), callbacks);
    if (payload !== null) {
      finalPayload = payload;
    }
  }
}

async function readSseStream(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  decoder: TextDecoder,
  callbacks?: StreamCallbacks,
): Promise<StreamEventMap["final"] | null> {
  let buffer = "";
  let finalPayload: StreamEventMap["final"] | null = null;

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const result = consumeSseBuffer(buffer, callbacks);
    buffer = result.remaining;
    if (result.finalPayload !== null) finalPayload = result.finalPayload;
  }

  buffer += decoder.decode();
  const result = consumeSseBuffer(buffer, callbacks);
  if (result.finalPayload !== null) finalPayload = result.finalPayload;
  return finalPayload;
}

async function streamProjectChat(
  projectId: string,
  message: string,
  callbacks?: StreamCallbacks,
): Promise<SendMessageResponse> {
  const response = await fetch(`${API_BASE}/agent/projects/${projectId}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(toErrorMessage(response, body));
  }
  if (response.body === null) {
    throw new Error("Streaming response body is unavailable");
  }

  const finalPayload = await readSseStream(response.body.getReader(), new TextDecoder(), callbacks);

  if (finalPayload === null) throw new Error("Stream completed without a final payload");
  if (!finalPayload.success) throw new Error(finalPayload.error ?? "Agent chat failed");
  if (finalPayload.project_state === undefined) {
    throw new Error("Agent chat succeeded but returned no project state");
  }
  return { message: finalPayload.answer, projectState: finalPayload.project_state };
}

export const chatApi = {
  async sendMessage(
    projectId: string,
    message: string,
    options?: {
      readonly idempotencyKey?: string;
      readonly callbacks?: StreamCallbacks;
    },
  ): Promise<SendMessageResponse> {
    void options?.idempotencyKey;
    return streamProjectChat(projectId, message, options?.callbacks);
  },

  async fetchMessages(
    projectId: string,
    sinceId?: string,
  ): Promise<readonly Message[]> {
    const url =
      sinceId !== undefined && sinceId !== ""
        ? `${API_BASE}/projects/${projectId}/messages?since_id=${sinceId}`
        : `${API_BASE}/projects/${projectId}/messages`;
    const data = await fetchWithErrorHandling<{
      readonly messages: readonly Message[];
    }>(url, {}, "fetch messages");
    return data.messages;
  },

  async fetchMessagesBefore(
    projectId: string,
    beforeMessageId: string,
    limit = 50,
  ): Promise<readonly Message[]> {
    const data = await fetchWithErrorHandling<{
      readonly messages: readonly Message[];
    }>(
      `${API_BASE}/projects/${projectId}/messages?before_id=${beforeMessageId}&limit=${limit}`,
      {},
      "fetch older messages",
    );
    return data.messages;
  },
};

export type { StreamCallbacks, StreamEventMap };
