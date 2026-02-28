import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { useProjectData } from "../../../../features/projects/hooks/useProjectData";
import type { Project } from "../../../../types/api";

vi.mock("../../../../services/projectService", () => ({
  projectApi: { get: vi.fn() },
}));

vi.mock("../../../../hooks/useToast", () => ({
  useToast: () => ({
    error: mockShowError,
    success: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
    show: vi.fn(),
    toasts: [],
    close: vi.fn(),
    closeAll: vi.fn(),
  }),
}));

const mockShowError = vi.fn();

import { projectApi } from "../../../../services/projectService";

const mockProjectApi = vi.mocked(projectApi);

const fakeProject: Project = {
  id: "p1",
  name: "Test",
  textRequirements: "Some requirements",
  createdAt: "2025-01-01T00:00:00Z",
};

describe("useProjectData", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("starts with null project and not loading", () => {
    const { result } = renderHook(() => useProjectData(undefined));
    expect(result.current.selectedProject).toBeNull();
    expect(result.current.loadingProject).toBe(false);
    expect(result.current.textRequirements).toBe("");
    expect(result.current.files).toBeNull();
  });

  it("does not fetch when projectId is undefined", async () => {
    renderHook(() => useProjectData(undefined));
    await act(async () => {});
    expect(mockProjectApi.get).not.toHaveBeenCalled();
  });

  it("does not fetch when projectId is empty", async () => {
    renderHook(() => useProjectData(""));
    await act(async () => {});
    expect(mockProjectApi.get).not.toHaveBeenCalled();
  });

  it("clears selected project when projectId becomes undefined", async () => {
    mockProjectApi.get.mockResolvedValue(fakeProject);
    const { result, rerender } = renderHook(
      ({ id }) => useProjectData(id),
      { initialProps: { id: "p1" as string | undefined } },
    );

    await act(async () => {});
    expect(result.current.selectedProject).toEqual(fakeProject);

    rerender({ id: undefined });
    await act(async () => {});

    expect(result.current.selectedProject).toBeNull();
  });

  it("fetches project and sets text requirements", async () => {
    mockProjectApi.get.mockResolvedValue(fakeProject);
    const { result } = renderHook(() => useProjectData("p1"));

    await act(async () => {});

    expect(mockProjectApi.get).toHaveBeenCalledWith("p1");
    expect(result.current.selectedProject).toEqual(fakeProject);
    expect(result.current.textRequirements).toBe("Some requirements");
    expect(result.current.loadingProject).toBe(false);
  });

  it("defaults textRequirements to empty when project has none", async () => {
    const noReqs: Project = { ...fakeProject, textRequirements: undefined };
    mockProjectApi.get.mockResolvedValue(noReqs);
    const { result } = renderHook(() => useProjectData("p1"));

    await act(async () => {});

    expect(result.current.textRequirements).toBe("");
  });

  it("shows toast on fetch error", async () => {
    mockProjectApi.get.mockRejectedValue(new Error("not found"));
    const { result } = renderHook(() => useProjectData("p1"));

    await act(async () => {});

    expect(mockShowError).toHaveBeenCalledWith(
      expect.stringContaining("not found"),
    );
    expect(result.current.loadingProject).toBe(false);
  });

  it("setSelectedProject updates state", async () => {
    const { result } = renderHook(() => useProjectData(undefined));

    act(() => {
      result.current.setSelectedProject(fakeProject);
    });

    expect(result.current.selectedProject).toEqual(fakeProject);
  });
});
