import { useCallback, useMemo, useState, useEffect, type Dispatch, type SetStateAction } from "react";
import type { WorkspaceTab } from "../components/unified/workspace/types";

export function useWorkspaceTabs(
  initialTabs: readonly WorkspaceTab[],
  resetKey?: string,
) {
  const [tabs, setTabs] = useState<readonly WorkspaceTab[]>(initialTabs);
  const [activeTabId, setActiveTabId] = useState(initialTabs[0]?.id ?? "");

  useEffect(() => {
    setTabs(initialTabs);
    setActiveTabId(initialTabs[0]?.id ?? "");
  }, [initialTabs, resetKey]);

  const orderedTabs = useMemo(() => normalizeTabs(tabs), [tabs]);

  const openTab = useCallback(createOpenTab(setTabs, setActiveTabId), []);
  const closeTab = useCallback(
    createCloseTab(setTabs, setActiveTabId, activeTabId),
    [activeTabId],
  );
  const togglePin = useCallback(createTogglePin(setTabs), []);
  const setDirty = useCallback(createSetDirty(setTabs), []);
  const reorderTabs = useCallback(createReorderTabs(setTabs), []);

  return {
    tabs: orderedTabs,
    activeTabId,
    setActiveTabId,
    openTab,
    closeTab,
    togglePin,
    setDirty,
    reorderTabs,
  };
}

function normalizeTabs(tabs: readonly WorkspaceTab[]): readonly WorkspaceTab[] {
  const pinned = tabs.filter((tab) => tab.pinned);
  const unpinned = tabs.filter((tab) => !tab.pinned);
  return [...pinned, ...unpinned];
}

function reorderTabList(
  tabs: readonly WorkspaceTab[],
  sourceId: string,
  targetId: string,
): readonly WorkspaceTab[] {
  const pinnedTabs = tabs.filter((tab) => tab.pinned);
  const unpinnedTabs = tabs.filter((tab) => !tab.pinned);

  const sourceInPinned = pinnedTabs.some((tab) => tab.id === sourceId);
  const targetInPinned = pinnedTabs.some((tab) => tab.id === targetId);

  if (sourceInPinned) {
    const nextPinned = moveWithinList({
      list: pinnedTabs,
      sourceId,
      targetId,
      fallbackToStart: targetInPinned,
    });
    if (!targetInPinned) {
      return [...nextPinned, ...unpinnedTabs];
    }
    return [...nextPinned, ...unpinnedTabs];
  }

  const nextUnpinned = moveWithinList({
    list: unpinnedTabs,
    sourceId,
    targetId,
    fallbackToStart: !targetInPinned,
  });
  return [...pinnedTabs, ...nextUnpinned];
}

function moveWithinList(
  params: {
    readonly list: readonly WorkspaceTab[];
    readonly sourceId: string;
    readonly targetId: string;
    readonly fallbackToStart: boolean;
  },
): readonly WorkspaceTab[] {
  const { list, sourceId, targetId, fallbackToStart } = params;
  const sourceIndex = list.findIndex((tab) => tab.id === sourceId);
  if (sourceIndex === -1) {
    return list;
  }
  const nextList = list.filter((tab) => tab.id !== sourceId);
  const targetIndex = list.findIndex((tab) => tab.id === targetId);

  if (targetIndex === -1) {
    const insertIndex = fallbackToStart ? 0 : nextList.length;
    return insertAt(nextList, list[sourceIndex], insertIndex);
  }

  return insertAt(nextList, list[sourceIndex], targetIndex);
}

function createOpenTab(
  setTabs: Dispatch<SetStateAction<readonly WorkspaceTab[]>>,
  setActiveTabId: Dispatch<SetStateAction<string>>,
) {
  return (tab: WorkspaceTab) => {
    setTabs((prev) => {
      const exists = prev.some((item) => item.id === tab.id);
      if (exists) {
        return prev;
      }
      return normalizeTabs([...prev, tab]);
    });
    setActiveTabId(tab.id);
  };
}

function createCloseTab(
  setTabs: Dispatch<SetStateAction<readonly WorkspaceTab[]>>,
  setActiveTabId: Dispatch<SetStateAction<string>>,
  activeTabId: string,
) {
  return (tabId: string) => {
    setTabs((prev) => {
      const nextTabs = prev.filter((tab) => tab.id !== tabId);
      if (nextTabs.length === 0) {
        return prev;
      }
      if (activeTabId === tabId) {
        const orderedNext = normalizeTabs(nextTabs);
        setActiveTabId(orderedNext[orderedNext.length - 1].id);
      }
      return nextTabs;
    });
  };
}

function createTogglePin(
  setTabs: Dispatch<SetStateAction<readonly WorkspaceTab[]>>,
) {
  return (tabId: string) => {
    setTabs((prev) => {
      const nextTabs = prev.map((tab) =>
        tab.id === tabId ? { ...tab, pinned: !tab.pinned } : tab,
      );
      return normalizeTabs(nextTabs);
    });
  };
}

function createSetDirty(
  setTabs: Dispatch<SetStateAction<readonly WorkspaceTab[]>>,
) {
  return (tabId: string, dirty: boolean) => {
    setTabs((prev) => prev.map((tab) =>
      tab.id === tabId ? { ...tab, dirty } : tab,
    ));
  };
}

function createReorderTabs(
  setTabs: Dispatch<SetStateAction<readonly WorkspaceTab[]>>,
) {
  return (sourceId: string, targetId: string) => {
    if (sourceId === targetId) {
      return;
    }
    setTabs((prev) => reorderTabList(prev, sourceId, targetId));
  };
}

function insertAt(
  list: readonly WorkspaceTab[],
  item: WorkspaceTab,
  index: number,
): readonly WorkspaceTab[] {
  const safeIndex = Math.max(0, Math.min(index, list.length));
  return [...list.slice(0, safeIndex), item, ...list.slice(safeIndex)];
}
