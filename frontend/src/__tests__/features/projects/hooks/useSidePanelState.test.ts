import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";
import { useSidePanelState } from "../../../../features/projects/hooks/useSidePanelState";

describe("useSidePanelState", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("defaults both panels to open when no localStorage", () => {
    const { result } = renderHook(() => useSidePanelState());
    expect(result.current.leftPanelOpen).toBe(true);
    expect(result.current.rightPanelOpen).toBe(true);
  });

  it("restores left panel state from localStorage", () => {
    localStorage.setItem("leftPanelOpen", "false");
    const { result } = renderHook(() => useSidePanelState());
    expect(result.current.leftPanelOpen).toBe(false);
  });

  it("restores right panel state from localStorage", () => {
    localStorage.setItem("rightPanelOpen", "false");
    const { result } = renderHook(() => useSidePanelState());
    expect(result.current.rightPanelOpen).toBe(false);
  });

  it("toggleLeftPanel flips the left panel", () => {
    const { result } = renderHook(() => useSidePanelState());
    expect(result.current.leftPanelOpen).toBe(true);

    act(() => {
      result.current.toggleLeftPanel();
    });
    expect(result.current.leftPanelOpen).toBe(false);

    act(() => {
      result.current.toggleLeftPanel();
    });
    expect(result.current.leftPanelOpen).toBe(true);
  });

  it("toggleRightPanel flips the right panel", () => {
    const { result } = renderHook(() => useSidePanelState());

    act(() => {
      result.current.toggleRightPanel();
    });
    expect(result.current.rightPanelOpen).toBe(false);
  });

  it("openLeftPanel forces left panel open", () => {
    localStorage.setItem("leftPanelOpen", "false");
    const { result } = renderHook(() => useSidePanelState());
    expect(result.current.leftPanelOpen).toBe(false);

    act(() => {
      result.current.openLeftPanel();
    });
    expect(result.current.leftPanelOpen).toBe(true);
  });

  it("openRightPanel forces right panel open", () => {
    localStorage.setItem("rightPanelOpen", "false");
    const { result } = renderHook(() => useSidePanelState());
    expect(result.current.rightPanelOpen).toBe(false);

    act(() => {
      result.current.openRightPanel();
    });
    expect(result.current.rightPanelOpen).toBe(true);
  });

  it("persists left panel state to localStorage", () => {
    const { result } = renderHook(() => useSidePanelState());

    act(() => {
      result.current.toggleLeftPanel();
    });

    expect(localStorage.getItem("leftPanelOpen")).toBe("false");
  });

  it("persists right panel state to localStorage", () => {
    const { result } = renderHook(() => useSidePanelState());

    act(() => {
      result.current.toggleRightPanel();
    });

    expect(localStorage.getItem("rightPanelOpen")).toBe("false");
  });
});
