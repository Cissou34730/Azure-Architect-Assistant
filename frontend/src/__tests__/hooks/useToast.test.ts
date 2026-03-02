import { renderHook, act } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { useToast } from "../../hooks/useToast";

describe("useToast", () => {
  it("starts with empty toasts", () => {
    const { result } = renderHook(() => useToast());
    expect(result.current.toasts).toEqual([]);
  });

  it("show adds a toast", () => {
    const { result } = renderHook(() => useToast());
    act(() => {
      result.current.show("Hello", "info");
    });
    expect(result.current.toasts).toHaveLength(1);
    expect(result.current.toasts[0].message).toBe("Hello");
    expect(result.current.toasts[0].type).toBe("info");
  });

  it("convenience methods set correct type", () => {
    const { result } = renderHook(() => useToast());
    act(() => {
      result.current.success("ok");
      result.current.error("fail");
      result.current.warning("warn");
      result.current.info("note");
    });
    const types = result.current.toasts.map((t) => t.type);
    expect(types).toEqual(["success", "error", "warning", "info"]);
  });

  it("close removes a specific toast", () => {
    const { result } = renderHook(() => useToast());
    let id = "";
    act(() => {
      id = result.current.show("A");
      result.current.show("B");
    });
    expect(result.current.toasts).toHaveLength(2);

    act(() => {
      result.current.close(id);
    });
    expect(result.current.toasts).toHaveLength(1);
    expect(result.current.toasts[0].message).toBe("B");
  });

  it("closeAll clears all toasts", () => {
    const { result } = renderHook(() => useToast());
    act(() => {
      result.current.show("A");
      result.current.show("B");
    });
    act(() => {
      result.current.closeAll();
    });
    expect(result.current.toasts).toEqual([]);
  });
});
