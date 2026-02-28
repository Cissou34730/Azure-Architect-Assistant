import { renderHook, act } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { useWorkspaceTabs } from "../../../../features/projects/hooks/useWorkspaceTabs";
import type { WorkspaceTab } from "../../../../features/projects/components/unified/workspace/types";

const tab = (id: string, pinned = false): WorkspaceTab => ({
  id,
  kind: "artifact-requirements",
  title: `Tab ${id}`,
  group: "artifact",
  pinned,
  dirty: false,
});

// Stable references to avoid infinite useEffect loops (initialTabs in deps)
const TABS_EMPTY: readonly WorkspaceTab[] = [];
const TABS_A: readonly WorkspaceTab[] = [tab("a")];
const TABS_AB: readonly WorkspaceTab[] = [tab("a"), tab("b")];
const TABS_ABC: readonly WorkspaceTab[] = [tab("a"), tab("b"), tab("c")];
const TABS_PINNED: readonly WorkspaceTab[] = [tab("a"), tab("b", true), tab("c")];

describe("useWorkspaceTabs", () => {
  it("initializes with given tabs and first tab active", () => {
    const { result } = renderHook(() => useWorkspaceTabs(TABS_AB));

    expect(result.current.tabs).toHaveLength(2);
    expect(result.current.activeTabId).toBe("a");
  });

  it("initializes with empty active when no tabs", () => {
    const { result } = renderHook(() => useWorkspaceTabs(TABS_EMPTY));
    expect(result.current.tabs).toHaveLength(0);
    expect(result.current.activeTabId).toBe("");
  });

  it("openTab adds a new tab and sets it active", () => {
    const { result } = renderHook(() => useWorkspaceTabs(TABS_A));

    act(() => {
      result.current.openTab(tab("b"));
    });

    expect(result.current.tabs).toHaveLength(2);
    expect(result.current.activeTabId).toBe("b");
  });

  it("openTab does not duplicate an existing tab", () => {
    const { result } = renderHook(() => useWorkspaceTabs(TABS_A));

    act(() => {
      result.current.openTab(tab("a"));
    });

    expect(result.current.tabs).toHaveLength(1);
    expect(result.current.activeTabId).toBe("a");
  });

  it("closeTab removes a tab", () => {
    const { result } = renderHook(() => useWorkspaceTabs(TABS_AB));

    act(() => {
      result.current.closeTab("b");
    });

    expect(result.current.tabs).toHaveLength(1);
    expect(result.current.tabs[0].id).toBe("a");
  });

  it("closeTab does not remove the last tab", () => {
    const { result } = renderHook(() => useWorkspaceTabs(TABS_A));

    act(() => {
      result.current.closeTab("a");
    });

    expect(result.current.tabs).toHaveLength(1);
  });

  it("closeTab selects another tab when active is closed", () => {
    const { result } = renderHook(() => useWorkspaceTabs(TABS_ABC));

    act(() => {
      result.current.setActiveTabId("b");
    });

    act(() => {
      result.current.closeTab("b");
    });

    expect(result.current.tabs).toHaveLength(2);
    // Should select the last normalized tab
    expect(result.current.activeTabId).toBe("c");
  });

  it("togglePin flips pinned flag and normalizes order", () => {
    const { result } = renderHook(() => useWorkspaceTabs(TABS_AB));

    act(() => {
      result.current.togglePin("b");
    });

    // "b" is now pinned, should be first
    expect(result.current.tabs[0].id).toBe("b");
    expect(result.current.tabs[0].pinned).toBe(true);
  });

  it("setDirty updates the dirty flag", () => {
    const { result } = renderHook(() => useWorkspaceTabs(TABS_A));

    act(() => {
      result.current.setDirty("a", true);
    });

    expect(result.current.tabs[0].dirty).toBe(true);
  });

  it("reorderTabs is noop when source equals target", () => {
    const { result } = renderHook(() => useWorkspaceTabs(TABS_AB));

    act(() => {
      result.current.reorderTabs("a", "a");
    });

    expect(result.current.tabs[0].id).toBe("a");
    expect(result.current.tabs[1].id).toBe("b");
  });

  it("reorderTabs moves unpinned tab to target position", () => {
    const { result } = renderHook(() => useWorkspaceTabs(TABS_ABC));

    act(() => {
      result.current.reorderTabs("c", "a");
    });

    expect(result.current.tabs.map((t) => t.id)).toEqual(["c", "a", "b"]);
  });

  it("normalizeTabs puts pinned first", () => {
    const { result } = renderHook(() => useWorkspaceTabs(TABS_PINNED));

    expect(result.current.tabs[0].id).toBe("b");
    expect(result.current.tabs[0].pinned).toBe(true);
  });

  it("resets tabs when resetKey changes", () => {
    const initial2: readonly WorkspaceTab[] = [tab("x")];

    const { result, rerender } = renderHook(
      ({ tabs, key }) => useWorkspaceTabs(tabs, key),
      { initialProps: { tabs: TABS_AB, key: "k1" } },
    );

    expect(result.current.tabs).toHaveLength(2);

    rerender({ tabs: initial2, key: "k2" });

    expect(result.current.tabs).toHaveLength(1);
    expect(result.current.tabs[0].id).toBe("x");
    expect(result.current.activeTabId).toBe("x");
  });
});
