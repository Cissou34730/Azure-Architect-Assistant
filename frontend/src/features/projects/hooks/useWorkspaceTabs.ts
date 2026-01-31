import { useCallback, useState } from "react";
import type { WorkspaceTab } from "../components/unified/workspace/types";

export function useWorkspaceTabs(initialTabs: readonly WorkspaceTab[]) {
  const [tabs, setTabs] = useState<readonly WorkspaceTab[]>(initialTabs);
  const [activeTabId, setActiveTabId] = useState(initialTabs[0]?.id ?? "");

  const openTab = useCallback((tab: WorkspaceTab) => {
    setTabs((prev) => {
      const exists = prev.some((item) => item.id === tab.id);
      if (exists) {
        return prev;
      }
      return [...prev, tab];
    });
    setActiveTabId(tab.id);
  }, []);

  const closeTab = useCallback((tabId: string) => {
    setTabs((prev) => {
      const nextTabs = prev.filter((tab) => tab.id !== tabId);
      if (nextTabs.length === 0) {
        return prev;
      }
      if (activeTabId === tabId) {
        setActiveTabId(nextTabs[nextTabs.length - 1].id);
      }
      return nextTabs;
    });
  }, [activeTabId]);

  return {
    tabs,
    activeTabId,
    setActiveTabId,
    openTab,
    closeTab,
  };
}
