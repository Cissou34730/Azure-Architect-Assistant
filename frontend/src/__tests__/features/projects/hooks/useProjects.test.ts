import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { useProjects } from "../../../../features/projects/hooks/useProjects";
import type { Project } from "../../../../types/api";

vi.mock("../../../../services/projectService", () => ({
  projectApi: {
    fetchAll: vi.fn(),
    create: vi.fn(),
  },
}));

import { projectApi } from "../../../../services/projectService";

const mockProjectApi = vi.mocked(projectApi);

const fakeProject: Project = {
  id: "p1",
  name: "Test",
  createdAt: "2025-01-01T00:00:00Z",
};

describe("useProjects", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("starts with empty projects and no selection", () => {
    const { result } = renderHook(() => useProjects());
    expect(result.current.projects).toEqual([]);
    expect(result.current.selectedProject).toBeNull();
    expect(result.current.loading).toBe(false);
  });

  it("fetchProjects populates the list", async () => {
    mockProjectApi.fetchAll.mockResolvedValue([fakeProject]);
    const { result } = renderHook(() => useProjects());

    await act(async () => {
      await result.current.fetchProjects();
    });

    expect(result.current.projects).toEqual([fakeProject]);
  });

  it("fetchProjects logs error on failure", async () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    mockProjectApi.fetchAll.mockRejectedValue(new Error("network"));
    const { result } = renderHook(() => useProjects());

    await act(async () => {
      await result.current.fetchProjects();
    });

    expect(spy).toHaveBeenCalledWith(expect.stringContaining("network"));
    spy.mockRestore();
  });

  it("createProject appends and auto-selects", async () => {
    mockProjectApi.create.mockResolvedValue(fakeProject);
    const { result } = renderHook(() => useProjects());

    let returned: Project | undefined;
    await act(async () => {
      returned = await result.current.createProject("Test");
    });

    expect(returned).toEqual(fakeProject);
    expect(result.current.projects).toEqual([fakeProject]);
    expect(result.current.selectedProject).toEqual(fakeProject);
  });

  it("createProject throws on empty name", async () => {
    const { result } = renderHook(() => useProjects());

    await expect(
      act(async () => {
        await result.current.createProject("  ");
      }),
    ).rejects.toThrow("Project name is required");
  });

  it("createProject resets loading on error", async () => {
    mockProjectApi.create.mockRejectedValue(new Error("server"));
    const { result } = renderHook(() => useProjects());

    await expect(
      act(async () => {
        await result.current.createProject("Test");
      }),
    ).rejects.toThrow("server");

    expect(result.current.loading).toBe(false);
  });

  it("setSelectedProject updates selection", () => {
    const { result } = renderHook(() => useProjects());

    act(() => {
      result.current.setSelectedProject(fakeProject);
    });

    expect(result.current.selectedProject).toEqual(fakeProject);
  });
});
