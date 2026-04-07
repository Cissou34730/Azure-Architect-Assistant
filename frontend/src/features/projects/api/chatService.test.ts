import { describe, expect, it, vi } from "vitest";

import { chatApi } from "./chatService";

function createStream(chunks: readonly string[]) {
  return new ReadableStream<Uint8Array>({
    start(controller) {
      const encoder = new TextEncoder();
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk));
      }
      controller.close();
    },
  });
}

describe("chatApi.sendMessage", () => {
  it("parses SSE events and returns the final project response", async () => {
    const events: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          createStream([
            'event: message_start\ndata: {"role":"assistant"}\n\n',
            'event: token\ndata: {"text":"Hello"}\n\n',
            'event: tool_start\ndata: {"tool":"kb_lookup","tool_input":{"query":"x"}}\n\n',
            'event: tool_result\ndata: {"tool":"kb_lookup","content":"done","status":"success"}\n\n',
            'event: final\ndata: {"answer":"Hello","success":true,"project_state":{"projectId":"p1"},"reasoning_steps":[],"error":null}\n\n',
          ]),
          {
            status: 200,
            headers: { "Content-Type": "text/event-stream" },
          },
        ),
      ),
    );

    const response = await chatApi.sendMessage("p1", "hello", {
      callbacks: {
        onMessageStart: () => events.push("message_start"),
        onToken: ({ text }) => events.push(`token:${text}`),
        onToolStart: ({ tool }) => events.push(`tool_start:${tool}`),
        onToolResult: ({ tool }) => events.push(`tool_result:${tool}`),
        onFinal: ({ answer }) => events.push(`final:${answer}`),
      },
    });

    expect(response).toEqual({
      message: "Hello",
      projectState: { projectId: "p1" },
    });
    expect(events).toEqual([
      "message_start",
      "token:Hello",
      "tool_start:kb_lookup",
      "tool_result:kb_lookup",
      "final:Hello",
    ]);
  });
});
