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
            'event: final\ndata: {"answer":"Hello","success":true,"project_state":{"projectId":"p1"},"reasoning_steps":[],"error":null,"thread_id":"thread-1","workflow_result":{"stage":"clarify","summary":"Hello","pendingChangeSet":null,"citations":[],"warnings":[],"nextStep":{"stage":"clarify","tool":null,"rationale":"Answer the clarification question.","blockingQuestions":["Which tenant?"]},"reasoningSummary":"Hello","toolCalls":[],"structuredPayload":{"type":"clarification_questions","questions":[{"id":"security-1","text":"Which tenant?","theme":"Security","whyItMatters":"Tenant boundaries change identity design.","architecturalImpact":"high","priority":1,"relatedRequirementIds":["req-auth"]}]}}}\n\n',
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
      workflowResult: {
        stage: "clarify",
        summary: "Hello",
        pendingChangeSet: null,
        citations: [],
        warnings: [],
        nextStep: {
          stage: "clarify",
          tool: null,
          rationale: "Answer the clarification question.",
          blockingQuestions: ["Which tenant?"],
        },
        reasoningSummary: "Hello",
        toolCalls: [],
        structuredPayload: {
          type: "clarification_questions",
          questions: [
            {
              id: "security-1",
              text: "Which tenant?",
              theme: "Security",
              whyItMatters: "Tenant boundaries change identity design.",
              architecturalImpact: "high",
              priority: 1,
              relatedRequirementIds: ["req-auth"],
            },
          ],
        },
      },
    });
    expect(events).toEqual([
      "message_start",
      "token:Hello",
      "tool_start:kb_lookup",
      "tool_result:kb_lookup",
      "final:Hello",
    ]);
  });

  it("surfaces SSE error events when the stream ends without a final payload", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          createStream([
            'event: error\ndata: {"error":"Graph execution failed: boom"}\n\n',
          ]),
          {
            status: 200,
            headers: { "Content-Type": "text/event-stream" },
          },
        ),
      ),
    );

    await expect(chatApi.sendMessage("p1", "hello")).rejects.toThrow(
      "Graph execution failed: boom",
    );
  });

  it("parses canonical stream events while preserving final payload compatibility", async () => {
    const events: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          createStream([
            'event: stage\ndata: {"stage":"clarify","confidence":1.0}\n\n',
            'event: text\ndata: {"delta":"Hello"}\n\n',
            'event: tool_call\ndata: {"tool":"kb_lookup","argsPreview":"{\\"query\\":\\"x\\"}"}\n\n',
            'event: tool_result\ndata: {"tool":"kb_lookup","resultPreview":"done","citations":["https://learn.microsoft.com/example"],"content":"done","status":"success"}\n\n',
            'event: pending_change\ndata: {"changeSetId":"cs-1","summary":"Review changes","patchCount":1}\n\n',
            'event: final\ndata: {"answer":"Hello","success":true,"project_state":{"projectId":"p1"},"reasoning_steps":[],"error":null,"thread_id":"thread-1","workflow_result":{"stage":"clarify","summary":"Hello","pendingChangeSet":null,"citations":[],"warnings":[],"nextStep":{"stage":"clarify","tool":null,"rationale":"Answer the clarification question.","blockingQuestions":["Which tenant?"]},"reasoningSummary":"Hello","toolCalls":[],"structuredPayload":{"type":"clarification_questions","questions":[{"id":"security-1","text":"Which tenant?","theme":"Security","whyItMatters":"Tenant boundaries change identity design.","architecturalImpact":"high","priority":1,"relatedRequirementIds":["req-auth"]}]}}}\n\n',
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
        onStage: ({ stage }) => events.push(`stage:${stage}`),
        onText: ({ delta }) => events.push(`text:${delta}`),
        onToolCall: ({ tool }) => events.push(`tool_call:${tool}`),
        onToolResult: ({ tool, resultPreview }) =>
          events.push(`tool_result:${tool}:${resultPreview}`),
        onPendingChange: ({ changeSetId }) => events.push(`pending_change:${changeSetId}`),
      },
    });

    expect(response.message).toBe("Hello");
    expect(response.projectState).toEqual({ projectId: "p1" });
    expect(events).toEqual([
      "stage:clarify",
      "text:Hello",
      "tool_call:kb_lookup",
      "tool_result:kb_lookup:done",
      "pending_change:cs-1",
    ]);
  });
});
