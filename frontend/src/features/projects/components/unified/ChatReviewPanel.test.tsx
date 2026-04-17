import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ChatReviewPanel } from "./ChatReviewPanel";
import { pendingChangesApi } from "../../api/pendingChangesService";
import type { ActiveChatReview } from "../../types/chat-review";

vi.mock("../../api/pendingChangesService", () => ({
  pendingChangesApi: {
    list: vi.fn(),
    get: vi.fn(),
    approve: vi.fn(),
    reject: vi.fn(),
  },
}));

const clarificationReview: ActiveChatReview = {
  assistantMessageId: "assistant-1",
  answerPreview: "I need one clarification before I can continue.",
  stageEvents: [{ stage: "clarify", confidence: 1 }],
  toolTraces: [
    {
      toolName: "kb_lookup",
      argsPreview: '{"query":"tenant"}',
      resultPreview: "Found Entra ID guidance.",
      citations: ["https://learn.microsoft.com/entra/fundamentals/"],
      durationMs: 1250,
      status: "completed",
    },
  ],
  pendingChangeSignal: {
    changeSetId: "change-1",
    summary: "Apply clarification answers to requirements.",
    patchCount: 2,
  },
  workflowResult: {
    stage: "clarify",
    summary: "I need one clarification before I can continue.",
    pendingChangeSet: null,
    citations: [
      {
        title: "Microsoft Learn - Entra fundamentals",
        url: "https://learn.microsoft.com/entra/fundamentals/",
        source: "learn.microsoft.com",
      },
    ],
    warnings: [],
    nextStep: {
      stage: "clarify",
      tool: null,
      rationale: "Collect the missing tenant decision.",
      blockingQuestions: ["Which Microsoft Entra tenant should host the workload?"],
    },
    reasoningSummary: "Missing tenant selection blocks identity design.",
    toolCalls: [
      {
        toolName: "kb_lookup",
        argsPreview: '{"query":"tenant"}',
        resultPreview: "Found Entra ID guidance.",
        citations: ["https://learn.microsoft.com/entra/fundamentals/"],
        durationMs: 1250,
      },
    ],
    structuredPayload: {
      type: "clarification_questions",
      questions: [
        {
          id: "security-1",
          text: "Which Microsoft Entra tenant should host the workload?",
          theme: "Security",
          whyItMatters: "Tenant choice changes identity boundaries and RBAC.",
          architecturalImpact: "high",
          priority: 1,
          relatedRequirementIds: ["req-auth-1"],
        },
      ],
    },
  },
};

describe("ChatReviewPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(pendingChangesApi.list).mockResolvedValue([
      {
        id: "change-1",
        projectId: "project-123",
        stage: "clarify",
        status: "pending",
        createdAt: "2026-04-17T10:00:00Z",
        sourceMessageId: "assistant-1",
        bundleSummary: "Apply clarification answers to requirements.",
        artifactCount: 2,
      },
    ]);
    vi.mocked(pendingChangesApi.get).mockResolvedValue({
      id: "change-1",
      projectId: "project-123",
      stage: "clarify",
      status: "pending",
      createdAt: "2026-04-17T10:00:00Z",
      sourceMessageId: "assistant-1",
      bundleSummary: "Apply clarification answers to requirements.",
      artifactCount: 2,
      proposedPatch: {
        requirements: [
          {
            operation: "update",
            artifactType: "requirement",
            title: "Identity boundary",
          },
        ],
      },
      artifactDrafts: [
        {
          id: "draft-1",
          artifactType: "requirement",
          artifactId: "req-auth-1",
          content: {
            title: "Identity boundary",
            text: "Use the shared enterprise tenant.",
          },
          citations: [],
          createdAt: "2026-04-17T10:00:00Z",
        },
      ],
      citations: [],
      reviewedAt: null,
      reviewReason: null,
    });
    vi.mocked(pendingChangesApi.approve).mockResolvedValue({
      changeSet: {
        id: "change-1",
        projectId: "project-123",
        stage: "clarify",
        status: "approved",
        createdAt: "2026-04-17T10:00:00Z",
        sourceMessageId: "assistant-1",
        bundleSummary: "Apply clarification answers to requirements.",
        artifactCount: 2,
        proposedPatch: {},
        artifactDrafts: [],
        citations: [],
        reviewedAt: "2026-04-17T10:05:00Z",
        reviewReason: null,
      },
      projectState: null,
      conflicts: [],
    });
  });

  it("renders the current workflow review with stages, citations, and tool traces", async () => {
    render(
      <ChatReviewPanel
        projectId="project-123"
        activeReview={{ ...clarificationReview, pendingChangeSignal: undefined }}
        onSendMessage={vi.fn()}
        onRefreshMessages={vi.fn()}
        onRefreshProjectState={vi.fn()}
      />,
    );

    expect(screen.getByText(/current workflow review/i)).toBeInTheDocument();
    expect(
      within(screen.getByLabelText(/workflow stage rail/i)).getByText(/clarify/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/security/i)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /tool trace/i }));

    expect(screen.getByText(/kb_lookup/i)).toBeInTheDocument();
    expect(screen.getByText(/found entra id guidance/i)).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /microsoft learn - entra fundamentals/i }),
    ).toHaveAttribute("href", "https://learn.microsoft.com/entra/fundamentals/");
  });

  it("submits grouped clarification answers through the existing chat action", async () => {
    const sendMessage = vi.fn().mockResolvedValue(undefined);

    render(
      <ChatReviewPanel
        projectId="project-123"
        activeReview={{ ...clarificationReview, pendingChangeSignal: undefined }}
        onSendMessage={sendMessage}
        onRefreshMessages={vi.fn()}
        onRefreshProjectState={vi.fn()}
      />,
    );

    await userEvent.type(
      screen.getByLabelText(/which microsoft entra tenant should host the workload/i),
      "Use the shared enterprise tenant.",
    );
    await userEvent.click(screen.getByRole("button", { name: /send clarification answers/i }));

    await waitFor(() => {
      expect(sendMessage).toHaveBeenCalledWith(
        expect.stringContaining("security-1"),
      );
    });
    expect(sendMessage).toHaveBeenCalledWith(
      expect.stringContaining("Use the shared enterprise tenant."),
    );
  });

  it("opens pending change review details and approves the selected change", async () => {
    const refreshProjectState = vi.fn().mockResolvedValue(undefined);
    const refreshMessages = vi.fn().mockResolvedValue(undefined);

    render(
      <ChatReviewPanel
        projectId="project-123"
        activeReview={clarificationReview}
        onSendMessage={vi.fn()}
        onRefreshMessages={refreshMessages}
        onRefreshProjectState={refreshProjectState}
      />,
    );

    const pendingChangeCard = await screen.findByTestId("pending-change-change-1");
    expect(
      within(pendingChangeCard).getAllByText(/identity boundary/i).length,
    ).toBeGreaterThan(0);

    await userEvent.click(within(pendingChangeCard).getByRole("button", { name: /approve/i }));

    await waitFor(() => {
      expect(pendingChangesApi.approve).toHaveBeenCalledWith("project-123", "change-1", null);
    });
    expect(refreshProjectState).toHaveBeenCalledTimes(1);
    expect(refreshMessages).toHaveBeenCalledTimes(1);
  });
});
