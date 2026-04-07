import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { useProjectOperations } from "../../../../features/projects/hooks/useProjectOperations";
import type { Project, ProjectState } from "../../../../features/projects/types/api-project";

const mockSuccess = vi.fn();
const mockShowError = vi.fn();
const mockWarning = vi.fn();

vi.mock("../../../../shared/hooks/useToast", () => ({
  useToast: () => ({
    success: mockSuccess,
    error: mockShowError,
    warning: mockWarning,
    info: vi.fn(),
    show: vi.fn(),
    toasts: [],
    close: vi.fn(),
    closeAll: vi.fn(),
  }),
}));

vi.mock("../../../../services/projectService", () => ({
  projectApi: {
    uploadDocuments: vi.fn(),
    saveTextRequirements: vi.fn(),
  },
}));

vi.mock("../../../../features/projects/hooks/useInputAnalysisWorkflow", () => ({
  useInputAnalysisWorkflow: () => ({
    state: {},
    isUploading: false,
    isAnalyzing: false,
    markUploadRunning: vi.fn(),
    markUploadSuccess: vi.fn(),
    markUploadError: vi.fn(),
    markAnalysisRunning: vi.fn(),
    markAnalysisSuccess: vi.fn(),
    markAnalysisError: vi.fn(),
    clearWorkflowMessage: vi.fn(),
  }),
}));

vi.mock("../../../../features/projects/hooks/useRequirementHandlers", () => ({
  useRequirementHandlers: vi.fn(() => ({
    handleSaveTextRequirements: vi.fn(),
    handleGenerateProposal: vi.fn(),
  })),
}));

const fakeProject: Project = {
  id: "p1",
  name: "Test",
  createdAt: "2025-01-01T00:00:00Z",
};

const fakeState = {
  projectId: "p1",
  referenceDocuments: [{ parseStatus: "parsed" }],
} as unknown as ProjectState;

const defaultProps = {
  selectedProject: fakeProject,
  setSelectedProject: vi.fn(),
  projectState: fakeState,
  files: null as FileList | null,
  setFiles: vi.fn(),
  textRequirements: "some requirements",
  analyzeDocuments: vi.fn().mockResolvedValue(fakeState),
  refreshState: vi.fn().mockResolvedValue(undefined),
  generateProposal: vi.fn(),
};

describe("useProjectOperations", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns operation handlers and workflow state", () => {
    const { result } = renderHook(() => useProjectOperations(defaultProps));

    expect(result.current.handleUploadDocuments).toBeDefined();
    expect(result.current.handleAnalyzeDocuments).toBeDefined();
    expect(result.current.handleSaveTextRequirements).toBeDefined();
    expect(result.current.handleGenerateProposal).toBeDefined();
    expect(result.current.inputWorkflow).toBeDefined();
    expect(result.current.isUploadingDocuments).toBe(false);
    expect(result.current.isAnalyzingDocuments).toBe(false);
  });

  it("handleAnalyzeDocuments warns when no inputs", async () => {
    const noInputProps = {
      ...defaultProps,
      selectedProject: { ...fakeProject, textRequirements: undefined },
      projectState: { ...fakeState, referenceDocuments: [] } as unknown as ProjectState,
      files: null,
      textRequirements: "",
    };

    const { result } = renderHook(() => useProjectOperations(noInputProps));

    await act(async () => {
      await result.current.handleAnalyzeDocuments();
    });

    expect(mockWarning).toHaveBeenCalledWith(
      expect.stringContaining("provide either text requirements"),
    );
  });

  it("handleAnalyzeDocuments does nothing when no project", async () => {
    const noProjectProps = { ...defaultProps, selectedProject: null };
    const { result } = renderHook(() => useProjectOperations(noProjectProps));

    await act(async () => {
      await result.current.handleAnalyzeDocuments();
    });

    expect(defaultProps.analyzeDocuments).not.toHaveBeenCalled();
  });

  it("handleUploadDocuments does nothing when no files", async () => {
    const { result } = renderHook(() => useProjectOperations(defaultProps));

    const preventDefault = vi.fn();
    const ev = { preventDefault } as unknown as React.SyntheticEvent;
    await act(async () => {
      await result.current.handleUploadDocuments(ev);
    });

    expect(preventDefault).toHaveBeenCalled();
  });
});

