import type { WorkspaceTab } from "./workspace/types";

export function shouldIgnoreKeyEvent(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) {
    return false;
  }
  const tag = target.tagName.toLowerCase();
  return tag === "input" || tag === "textarea" || target.isContentEditable;
}

export function shouldHandleTabShortcut(event: KeyboardEvent): boolean {
  const isCmdOrCtrl = event.metaKey || event.ctrlKey;
  if (!isCmdOrCtrl) return false;
  return !shouldIgnoreKeyEvent(event.target);
}

export function getNextTabIndex(currentIndex: number, total: number, reverse: boolean): number {
  if (total === 0) return 0;
  if (currentIndex < 0) return 0;
  const direction = reverse ? -1 : 1;
  return (currentIndex + direction + total) % total;
}

export function cycleTab({
  tabs,
  activeTabId,
  onTabChange,
  reverse,
}: {
  readonly tabs: readonly WorkspaceTab[];
  readonly activeTabId: string;
  readonly onTabChange: (tabId: string) => void;
  readonly reverse: boolean;
}) {
  if (tabs.length === 0) return;
  const currentIndex = tabs.findIndex((tab) => tab.id === activeTabId);
  const nextIndex = getNextTabIndex(currentIndex, tabs.length, reverse);
  onTabChange(tabs[nextIndex].id);
}

export function focusTabIndex({
  tabs,
  index,
  onTabChange,
}: {
  readonly tabs: readonly WorkspaceTab[];
  readonly index: number;
  readonly onTabChange: (tabId: string) => void;
}) {
  if (index < 0 || index >= tabs.length) return;
  onTabChange(tabs[index].id);
}

export function handleTabShortcut({
  event,
  tabs,
  activeTabId,
  onCloseTab,
  onTabChange,
}: {
  readonly event: KeyboardEvent;
  readonly tabs: readonly WorkspaceTab[];
  readonly activeTabId: string;
  readonly onCloseTab: (tabId: string) => void;
  readonly onTabChange: (tabId: string) => void;
}) {
  const key = event.key.toLowerCase();
  if (key === "w") {
    event.preventDefault();
    if (activeTabId !== "") {
      onCloseTab(activeTabId);
    }
    return;
  }

  if (event.key === "Tab") {
    event.preventDefault();
    cycleTab({ tabs, activeTabId, onTabChange, reverse: event.shiftKey });
    return;
  }

  if (/^[1-9]$/.test(event.key)) {
    event.preventDefault();
    focusTabIndex({ tabs, index: Number(event.key) - 1, onTabChange });
  }
}
