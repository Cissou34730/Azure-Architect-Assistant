import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { useProjectState } from "../../../../features/projects/hooks/useProjectState";
import type { ProjectState } from "../../../../types/api";

vi.mock("../../../../services/stateService", () => ({
  stateApi: { fetch: vi.fn() },
}));

vi.mock("../../../../services/projectService", () => ({
  projectApi: { analyzeDocuments: vi.fn() },
}));

import { stateApi } from "../../../../services/stateService";
import { projectApi } from "../../../../services/projectService";

const mockStateApi = vi.mocked(stateApi);
const mockProjectApi = vi.mocked(projectApi);

const fakeState = { projectId: "p1", lastUpdated: "2025-01-01" } as unknown as ProjectState;

describe("useProjectState", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("starts with null state and not loading", () => {
    mockStateApi.fetch.mockResolvedValue(null);
    const { result } = renderHook(() => useProjectState(null));
    expect(result.current.projectState).toBeNull();
    expect(result.current.loading).toBe(false);
  });

  it("does not fetch when projectId is null", async () => {
    renderHook(() => useProjectState(null));
    // Wait a tick for any potential effects
    await act(async () => {});
    expect(mockStateApi.fetch).not.toHaveBeenCalled();
  });

  it("does not fetch when projectId is empty", async () => {
    renderHook(() => useProjectState(""));
    await act(async () => {});
    expect(mockStateApi.fetch).not.toHaveBeenCalled();
  });

  it("fetches state on mount when projectId is valid", async () => {
    mockStateApi.fetch.mockResolvedValue(fakeState);
    const { result } = renderHook(() => useProjectState("p1"));

    await act(async () => {});

    expect(mockStateApi.fetch).toHaveBeenCalledWith("p1");
    expect(result.current.projectState).toEqual(fakeState);
  });

  it("re-fetches when projectId changes", async () => {
    mockStateApi.fetch.mockResolvedValue(fakeState);
    const { rerender } = renderHook(
      ({ id }) => useProjectState(id),
      { initialProps: { id: "p1" as string | null } },
    );

    await act(async () => {});
    expect(mockStateApi.fetch).toHaveBeenCalledWith("p1");

    const newState = { ...fakeState, projectId: "p2" } as unknown as ProjectState;
    mockStateApi.fetch.mockResolvedValue(newState);

    rerender({ id: "p2" });
    await act(async () => {});

    expect(mockStateApi.fetch).toHaveBeenCalledWith("p2");
  });

  it("analyzeDocuments throws when no project selected", async () => {
    const { result } = renderHook(() => useProjectState(null));

    await expect(
      act(async () => {
        await result.current.analyzeDocuments();
      }),
    ).rejects.toThrow("No project selected");
  });

  it("analyzeDocuments calls API and updates state", async () => {
    mockStateApi.fetch.mockResolvedValue(null);
    mockProjectApi.analyzeDocuments.mockResolvedValue(fakeState);
    const { result } = renderHook(() => useProjectState("p1"));
    await act(async () => {});

    let returned: ProjectState | undefined;
    await act(async () => {
      returned = await result.current.analyzeDocuments();
    });

    expect(mockProjectApi.analyzeDocuments).toHaveBeenCalledWith("p1");
    expect(returned).toEqual(fakeState);
    expect(result.current.projectState).toEqual(fakeState);
    expect(result.current.loading).toBe(false);
  });

  it("analyzeDocuments resets loading on error", async () => {
    mockStateApi.fetch.mockResolvedValue(null);
    mockProjectApi.analyzeDocuments.mockRejectedValue(new Error("fail"));
    const { result } = renderHook(() => useProjectState("p1"));
    await act(async () => {});

    await expect(
      act(async () => {
        await result.current.analyzeDocuments();
      }),
    ).rejects.toThrow("fail");

    expect(result.current.loading).toBe(false);
  });

  it("logs error when fetch fails", async () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    mockStateApi.fetch.mockRejectedValue(new Error("network"));
    renderHook(() => useProjectState("p1"));

    await act(async () => {});

    expect(spy).toHaveBeenCalledWith(expect.stringContaining("network"));
    spy.mockRestore();
  });
});
