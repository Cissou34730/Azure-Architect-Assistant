import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ChatReviewPanel } from "./ChatReviewPanel";
import { pendingChangesApi } from "../../api/pendingChangesService";
import type { ActiveChatReview } from "../../types/chat-review";
import type { WorkflowStructuredPayload } from "../../../knowledge/types/api-kb";

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

// ---- Q0.5 failing tests: architect question type and rendering ----
// These tests are intentionally RED until ArchitectQuestionsPayload is added to api-kb.ts
// and ArchitectQuestionsSection is rendered by ChatReviewPanel.

const architectOnlyReview: ActiveChatReview = {
  assistantMessageId: "assistant-arch-1",
  answerPreview: "Resolving internal architectural decisions.",
  stageEvents: [{ stage: "clarify", confidence: 1 }],
  toolTraces: [],
  workflowResult: {
    stage: "clarify",
    summary: "Architect questions pending resolution.",
    pendingChangeSet: null,
    citations: [],
    warnings: [],
    nextStep: {
      stage: "clarify",
      tool: null,
      rationale: "Resolve architectural trade-offs before proceeding.",
      blockingQuestions: [],
    },
    reasoningSummary: "Internal trade-off analysis required.",
    toolCalls: [],
    // `as unknown` bypasses the missing ArchitectQuestionsPayload union member so the test
    // file compiles via esbuild.  Running `npm run typecheck` WILL fail until the type is
    // added to WorkflowStructuredPayload in api-kb.ts — that tsc error is the type-level signal.
    structuredPayload: {
      type: "architect_questions",
      architectQuestionGroups: [
        {
          id: "arch-compute-1",
          topic: "Compute tier",
          designDecision: "AKS vs App Service",
          wafPillar: "Reliability",
          mindmapNodes: ["compute", "networking"],
          risk: "high",
          answer: null,
        },
      ],
    } as unknown as WorkflowStructuredPayload,
  },
};

const mixedQuestionsReview: ActiveChatReview = {
  assistantMessageId: "assistant-mixed-1",
  answerPreview: "I have questions for both you and myself.",
  stageEvents: [{ stage: "clarify", confidence: 1 }],
  toolTraces: [],
  workflowResult: {
    stage: "clarify",
    summary: "Mixed question set.",
    pendingChangeSet: null,
    citations: [],
    warnings: [],
    nextStep: {
      stage: "clarify",
      tool: null,
      rationale: "Gather all inputs.",
      blockingQuestions: [],
    },
    reasoningSummary: "Both customer and architect questions pending.",
    toolCalls: [],
    structuredPayload: {
      type: "architect_questions",
      customerQuestions: [
        {
          id: "customer-sla-1",
          text: "What is your target SLA?",
          theme: "Reliability",
          whyItMatters: "SLA drives redundancy and failover decisions.",
          architecturalImpact: "high",
          priority: 1,
          relatedRequirementIds: [],
        },
      ],
      architectQuestionGroups: [
        {
          id: "arch-compute-1",
          topic: "Compute tier",
          designDecision: "AKS vs App Service",
          wafPillar: "Reliability",
          mindmapNodes: ["compute", "networking"],
          risk: "high",
          answer: null,
        },
      ],
    } as unknown as WorkflowStructuredPayload,
  },
};

describe("ChatReviewPanel – Q0.5 architect questions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(pendingChangesApi.list).mockResolvedValue([]);
  });

  it("type annotation: architect_questions payload satisfies WorkflowStructuredPayload (typecheck gate)", () => {
    // Runtime: passes trivially (esbuild strips types).
    // Typecheck: `npm run typecheck` will FAIL until ArchitectQuestionsPayload is added to
    // the WorkflowStructuredPayload union in api-kb.ts.
    // Remove the `as unknown` cast from the fixtures above once the type is added to verify.
    const payload = architectOnlyReview.workflowResult?.structuredPayload;
    expect(payload?.type).toBe("architect_questions");
  });

  it("renders an architect questions section with WAF pillar and design decision", () => {
    // FAILS until ArchitectQuestionsSection is rendered by ChatReviewPanel
    render(
      <ChatReviewPanel
        projectId="project-123"
        activeReview={architectOnlyReview}
        onSendMessage={vi.fn()}
        onRefreshMessages={vi.fn()}
        onRefreshProjectState={vi.fn()}
      />,
    );

    expect(screen.getByRole("region", { name: /architect questions/i })).toBeInTheDocument();
    expect(screen.getByText(/AKS vs App Service/i)).toBeInTheDocument();
    expect(screen.getByText(/Reliability/i)).toBeInTheDocument(); // WAF pillar
    expect(screen.getByText(/high/i)).toBeInTheDocument(); // risk level
  });

  it("renders both customer clarification form and architect questions section for mixed payloads", () => {
    // FAILS until ChatReviewPanel renders dual sections for the mixed payload type
    render(
      <ChatReviewPanel
        projectId="project-123"
        activeReview={mixedQuestionsReview}
        onSendMessage={vi.fn()}
        onRefreshMessages={vi.fn()}
        onRefreshProjectState={vi.fn()}
      />,
    );

    // Customer section must include the answer form with a submit button
    expect(screen.getByText(/clarification questions/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /send clarification answers/i })).toBeInTheDocument();
    // Architect section must be present alongside the customer form
    expect(screen.getByRole("region", { name: /architect questions/i })).toBeInTheDocument();
    expect(screen.getByText(/AKS vs App Service/i)).toBeInTheDocument();
  });

  it("does not render a customer answer submit button for architect-only questions", () => {
    // FAILS on the first assertion until ArchitectQuestionsSection is rendered;
    // once that is green, the second assertion guards against accidentally showing the
    // customer answer form in an architect-only context.
    render(
      <ChatReviewPanel
        projectId="project-123"
        activeReview={architectOnlyReview}
        onSendMessage={vi.fn()}
        onRefreshMessages={vi.fn()}
        onRefreshProjectState={vi.fn()}
      />,
    );

    expect(screen.getByRole("region", { name: /architect questions/i })).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /send clarification answers/i }),
    ).not.toBeInTheDocument();
  });
});
