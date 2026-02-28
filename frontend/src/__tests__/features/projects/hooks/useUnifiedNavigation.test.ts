import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { useUnifiedNavigation } from "../../../../features/projects/hooks/useUnifiedNavigation";
import type { NavigateFunction } from "react-router-dom";

describe("useUnifiedNavigation", () => {
  const mockNavigate = vi.fn() as unknown as NavigateFunction;

  it("handleNavigateToDiagrams navigates with correct path", () => {
    const { result } = renderHook(() =>
      useUnifiedNavigation("p1", mockNavigate),
    );

    act(() => {
      result.current.handleNavigateToDiagrams();
    });

    expect(mockNavigate).toHaveBeenCalledWith("/project/p1?tab=diagrams");
  });

  it("handleNavigateToAdrs navigates with correct path", () => {
    const { result } = renderHook(() =>
      useUnifiedNavigation("p1", mockNavigate),
    );

    act(() => {
      result.current.handleNavigateToAdrs();
    });

    expect(mockNavigate).toHaveBeenCalledWith("/project/p1?tab=adrs");
  });

  it("handleNavigateToCosts navigates with correct path", () => {
    const { result } = renderHook(() =>
      useUnifiedNavigation("p1", mockNavigate),
    );

    act(() => {
      result.current.handleNavigateToCosts();
    });

    expect(mockNavigate).toHaveBeenCalledWith("/project/p1?tab=costs");
  });

  it("does nothing when projectId is undefined", () => {
    const nav = vi.fn() as unknown as NavigateFunction;
    const { result } = renderHook(() =>
      useUnifiedNavigation(undefined, nav),
    );

    act(() => {
      result.current.handleNavigateToDiagrams();
    });

    expect(nav).not.toHaveBeenCalled();
  });

  it("does nothing when projectId is empty", () => {
    const nav = vi.fn() as unknown as NavigateFunction;
    const { result } = renderHook(() =>
      useUnifiedNavigation("", nav),
    );

    act(() => {
      result.current.handleNavigateToAdrs();
    });

    expect(nav).not.toHaveBeenCalled();
  });
});
