import { renderHook } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { useProjectDetails } from "../../../../features/projects/hooks/useProjectDetails";
import type { Project, ProjectState } from "../../../../features/projects/types/api-project";

const fakeProject: Project = {
  id: "p1",
  name: "Test",
  createdAt: "2025-01-01T00:00:00Z",
};

const fakeState = {
  projectId: "p1",
  lastUpdated: "2025-01-01",
} as unknown as ProjectState;

const mockSetProjectState = vi.fn();
const mockAnalyze = vi.fn();
const mockRefreshState = vi.fn();
const mockSendMessage = vi.fn().mockResolvedValue({});
const mockGenerateProposal = vi.fn();

vi.mock("../../../../features/projects/hooks/useProjectData", () => ({
  useProjectData: vi.fn(() => ({
    selectedProject: fakeProject,
    setSelectedProject: vi.fn(),
    loadingProject: false,
    textRequirements: "",
    setTextRequirements: vi.fn(),
    files: null,
    setFiles: vi.fn(),
  })),
}));

vi.mock("../../../../features/projects/hooks/useProjectState", () => ({
  useProjectState: vi.fn(() => ({
    projectState: fakeState,
    setProjectState: mockSetProjectState,
    loading: false,
    analyzeDocuments: mockAnalyze,
    refreshState: mockRefreshState,
  })),
}));

vi.mock("../../../../features/projects/hooks/useChat", () => ({
  useChat: vi.fn(() => ({
    messages: [],
    chatInput: "",
    setChatInput: vi.fn(),
    loading: false,
    loadingMessage: "",
    sendMessage: mockSendMessage,
    refreshMessages: vi.fn(),
    fetchOlderMessages: vi.fn(),
    failedMessages: [],
    retrySendMessage: vi.fn(),
  })),
}));

vi.mock("../../../../features/projects/hooks/useProposal", () => ({
  useProposal: vi.fn(() => ({
    architectureProposal: "",
    proposalStage: "",
    loading: false,
    generateProposal: mockGenerateProposal,
  })),
}));

vi.mock("../../../../features/projects/hooks/useChatHandlers", () => ({
  useChatHandlers: vi.fn(() => ({
    handleSendChatMessage: vi.fn(),
  })),
}));

vi.mock("../../../../features/projects/hooks/useProjectOperations", () => ({
  useProjectOperations: vi.fn(() => ({
    handleUploadDocuments: vi.fn(),
    handleAnalyzeDocuments: vi.fn(),
    handleSaveTextRequirements: vi.fn(),
    handleGenerateProposal: vi.fn(),
    inputWorkflow: {},
    isUploadingDocuments: false,
    isAnalyzingDocuments: false,
    clearInputWorkflowMessage: vi.fn(),
  })),
}));

vi.mock("../../../../features/projects/hooks/useProjectLoading", () => ({
  useProjectLoading: vi.fn(() => false),
}));

describe("useProjectDetails", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns aggregated fields from composed hooks", () => {
    const { result } = renderHook(() => useProjectDetails("p1"));

    expect(result.current.selectedProject).toEqual(fakeProject);
    expect(result.current.projectState).toEqual(fakeState);
    expect(result.current.loading).toBe(false);
    expect(result.current.messages).toEqual([]);
    expect(result.current.chatInput).toBe("");
    expect(result.current.architectureProposal).toBe("");
  });

  it("provides operation handlers", () => {
    const { result } = renderHook(() => useProjectDetails("p1"));

    expect(result.current.handleUploadDocuments).toBeDefined();
    expect(result.current.handleAnalyzeDocuments).toBeDefined();
    expect(result.current.handleSaveTextRequirements).toBeDefined();
    expect(result.current.handleGenerateProposal).toBeDefined();
    expect(result.current.handleSendChatMessage).toBeDefined();
  });

  it("provides refresh functions", () => {
    const { result } = renderHook(() => useProjectDetails("p1"));

    expect(result.current.refreshState).toBeDefined();
    expect(result.current.refreshMessages).toBeDefined();
    expect(result.current.analyzeDocuments).toBeDefined();
  });
});
