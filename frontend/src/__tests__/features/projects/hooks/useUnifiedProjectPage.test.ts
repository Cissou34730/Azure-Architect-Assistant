import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { useUnifiedProjectPage } from "../../../../features/projects/hooks/useUnifiedProjectPage";

const mockNavigate = vi.fn();
const mockOpenLeftPanel = vi.fn();

vi.mock("react-router-dom", () => ({
  useParams: () => ({ projectId: "p1" }),
  useNavigate: () => mockNavigate,
}));

vi.mock("../../../../features/projects/context/useProjectMetaContext", () => ({
  useProjectMetaContext: () => ({ loadingProject: false }),
}));

vi.mock("../../../../features/projects/context/useProjectStateContext", () => ({
  useProjectStateContext: () => ({
    projectState: { projectId: "p1" },
    loading: false,
  }),
}));

vi.mock("../../../../features/projects/context/useProjectChatContext", () => ({
  useProjectChatContext: () => ({ loading: false }),
}));

vi.mock("../../../../features/projects/hooks/useSidePanelState", () => ({
  useSidePanelState: () => ({
    leftPanelOpen: true,
    rightPanelOpen: true,
    toggleLeftPanel: vi.fn(),
    toggleRightPanel: vi.fn(),
    openLeftPanel: mockOpenLeftPanel,
    openRightPanel: vi.fn(),
  }),
}));

vi.mock("../../../../features/projects/hooks/useUnifiedNavigation", () => ({
  useUnifiedNavigation: () => ({
    handleNavigateToDiagrams: vi.fn(),
    handleNavigateToAdrs: vi.fn(),
    handleNavigateToCosts: vi.fn(),
  }),
}));

describe("useUnifiedProjectPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns projectId from route params", () => {
    const { result } = renderHook(() => useUnifiedProjectPage());
    expect(result.current.projectId).toBe("p1");
  });

  it("aggregates loading from all contexts", () => {
    const { result } = renderHook(() => useUnifiedProjectPage());
    expect(result.current.loading).toBe(false);
  });

  it("returns projectState from context", () => {
    const { result } = renderHook(() => useUnifiedProjectPage());
    expect(result.current.projectState).toEqual({ projectId: "p1" });
  });

  it("returns panel state", () => {
    const { result } = renderHook(() => useUnifiedProjectPage());
    expect(result.current.leftPanelOpen).toBe(true);
    expect(result.current.rightPanelOpen).toBe(true);
  });

  it("handleUploadClick opens left panel and dispatches event", () => {
    const dispatchSpy = vi.spyOn(window, "dispatchEvent");
    const { result } = renderHook(() => useUnifiedProjectPage());

    act(() => {
      result.current.handleUploadClick();
    });

    expect(mockOpenLeftPanel).toHaveBeenCalled();
    expect(dispatchSpy).toHaveBeenCalledWith(
      expect.objectContaining({ type: "open-documents-tab" }),
    );
    dispatchSpy.mockRestore();
  });

  it("returns navigation handlers", () => {
    const { result } = renderHook(() => useUnifiedProjectPage());
    expect(result.current.handleNavigateToDiagrams).toBeDefined();
    expect(result.current.handleNavigateToAdrs).toBeDefined();
    expect(result.current.handleNavigateToCosts).toBeDefined();
  });
});
