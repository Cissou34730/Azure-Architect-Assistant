import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";
import { usePanelWidth } from "../../../../features/projects/hooks/usePanelWidth";

const defaultOpts = {
  storageKey: "test-panel-width",
  defaultWidth: 300,
  minWidth: 200,
  maxWidth: 600,
};

describe("usePanelWidth", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("uses defaultWidth when no stored value", () => {
    const { result } = renderHook(() => usePanelWidth(defaultOpts));
    expect(result.current.width).toBe(300);
  });

  it("restores width from localStorage", () => {
    localStorage.setItem("test-panel-width", "400");
    const { result } = renderHook(() => usePanelWidth(defaultOpts));
    expect(result.current.width).toBe(400);
  });

  it("clamps stored value to min", () => {
    localStorage.setItem("test-panel-width", "100");
    const { result } = renderHook(() => usePanelWidth(defaultOpts));
    expect(result.current.width).toBe(200);
  });

  it("clamps stored value to max", () => {
    localStorage.setItem("test-panel-width", "999");
    const { result } = renderHook(() => usePanelWidth(defaultOpts));
    expect(result.current.width).toBe(600);
  });

  it("falls back to defaultWidth on non-numeric stored value", () => {
    localStorage.setItem("test-panel-width", "abc");
    const { result } = renderHook(() => usePanelWidth(defaultOpts));
    expect(result.current.width).toBe(300);
  });

  it("setWidth clamps to bounds", () => {
    const { result } = renderHook(() => usePanelWidth(defaultOpts));

    act(() => {
      result.current.setWidth(100);
    });
    expect(result.current.width).toBe(200);

    act(() => {
      result.current.setWidth(999);
    });
    expect(result.current.width).toBe(600);
  });

  it("setWidth accepts values within range", () => {
    const { result } = renderHook(() => usePanelWidth(defaultOpts));

    act(() => {
      result.current.setWidth(450);
    });
    expect(result.current.width).toBe(450);
  });

  it("persists width to localStorage", () => {
    const { result } = renderHook(() => usePanelWidth(defaultOpts));

    act(() => {
      result.current.setWidth(500);
    });

    expect(localStorage.getItem("test-panel-width")).toBe("500");
  });
});
