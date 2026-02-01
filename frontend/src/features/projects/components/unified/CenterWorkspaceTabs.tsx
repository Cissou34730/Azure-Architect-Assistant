import { useMemo, useEffect, useState, useCallback } from "react";
import { Pin } from "lucide-react";
import { useProjectStateContext } from "../../context/useProjectStateContext";
import type { WorkspaceTab } from "./workspace/types";
import { WorkspaceTabContent } from "./workspace/WorkspaceTabContent";

interface CenterWorkspaceTabsProps {
  readonly tabs: readonly WorkspaceTab[];
  readonly activeTabId: string;
  readonly onTabChange: (tabId: string) => void;
  readonly onCloseTab: (tabId: string) => void;
  readonly onTogglePin: (tabId: string) => void;
  readonly onReorderTab: (sourceId: string, targetId: string) => void;
}

const TAB_BADGE_CLASS: Record<"input" | "artifact", string> = {
  input: "bg-emerald-600 text-white border-emerald-600",
  artifact: "bg-blue-600 text-white border-blue-600",
};

function TabBadge({ group }: { readonly group: "input" | "artifact" }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase ${TAB_BADGE_CLASS[group]}`}
    >
      {group === "input" ? "Input" : "Artifact"}
    </span>
  );
}

export function CenterWorkspaceTabs({
  tabs,
  activeTabId,
  onTabChange,
  onCloseTab,
  onTogglePin,
  onReorderTab,
}: CenterWorkspaceTabsProps) {
  const { projectState } = useProjectStateContext();
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const documents = useMemo(
    () => projectState?.referenceDocuments ?? [],
    [projectState?.referenceDocuments],
  );

  const hasArtifacts = useMemo(() => {
    if (projectState === null) {
      return false;
    }
    return (
      projectState.requirements.length > 0 ||
      projectState.adrs.length > 0 ||
      projectState.diagrams.length > 0 ||
      projectState.findings.length > 0 ||
      projectState.iacArtifacts.length > 0 ||
      projectState.costEstimates.length > 0
    );
  }, [projectState]);

  const activeTab =
    tabs.length > 0 ? (tabs.find((tab) => tab.id === activeTabId) ?? tabs[0]) : null;
  const hasActiveTab = activeTab !== null && tabs.length > 0;
  const resolvedActiveTabId = activeTab?.id ?? "";

  useTabKeyboardNavigation({
    tabs,
    activeTabId: activeTab?.id ?? "",
    onCloseTab,
    onTabChange,
  });

  return (
    <div className="flex flex-col h-full bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
      <div className="flex items-center justify-between px-3 py-2 bg-slate-900 text-white text-xs font-semibold uppercase tracking-wide">
        <span>Workspace Tabs</span>
        <span className="text-slate-200">{tabs.length} open</span>
      </div>
      <TabStrip
        tabs={tabs}
        activeTabId={resolvedActiveTabId}
        onTabChange={onTabChange}
        onCloseTab={onCloseTab}
        onTogglePin={onTogglePin}
        onReorderTab={onReorderTab}
        draggingId={draggingId}
        setDraggingId={setDraggingId}
      />

      <div className="flex-1 overflow-hidden bg-white">
        {hasActiveTab ? (
          <WorkspaceTabContent tab={activeTab} documents={documents} hasArtifacts={hasArtifacts} />
        ) : (
          <div className="h-full flex items-center justify-center text-sm text-gray-500">
            Select an input or artifact from the left panel.
          </div>
        )}
      </div>
    </div>
  );
}

interface TabStripProps {
  readonly tabs: readonly WorkspaceTab[];
  readonly activeTabId: string;
  readonly onTabChange: (tabId: string) => void;
  readonly onCloseTab: (tabId: string) => void;
  readonly onTogglePin: (tabId: string) => void;
  readonly onReorderTab: (sourceId: string, targetId: string) => void;
  readonly draggingId: string | null;
  readonly setDraggingId: (value: string | null) => void;
}

function TabStrip({
  tabs,
  activeTabId,
  onTabChange,
  onCloseTab,
  onTogglePin,
  onReorderTab,
  draggingId,
  setDraggingId,
}: TabStripProps) {
  return (
    <div className="border-b border-gray-200 bg-slate-200">
      <div className="flex items-stretch overflow-x-auto" role="tablist" aria-label="Workspace tabs">
        {tabs.length === 0 ? (
          <div className="px-3 py-2 text-xs text-slate-600">No tabs open</div>
        ) : (
          tabs.map((tab) => {
          const isActive = tab.id === activeTabId;
          const isPinned = tab.pinned;
          const accentClass =
            tab.group === "input" ? "border-emerald-500" : "border-blue-500";
          const titleClass =
            tab.group === "input" ? "text-emerald-700" : "text-blue-700";
          return (
            <div
              key={tab.id}
              draggable
              onDragStart={() => {
                setDraggingId(tab.id);
              }}
              onDragOver={(event) => {
                event.preventDefault();
              }}
              onDrop={() => {
                if (draggingId !== null) {
                  onReorderTab(draggingId, tab.id);
                }
                setDraggingId(null);
              }}
              className={`group relative flex items-stretch border-r border-t-2 ${
                isActive
                  ? `bg-white ${accentClass} border-r-gray-200`
                  : "bg-slate-200 border-transparent hover:bg-slate-100"
              }`}
            >
              <button
                type="button"
                onClick={() => { onTabChange(tab.id); }}
                className={`flex items-center gap-2 px-3 text-xs font-medium h-9 ${
                  isActive
                    ? "text-gray-900 border-b-2 border-slate-900/10"
                    : "text-gray-700"
                }`}
                role="tab"
                aria-selected={isActive}
              >
                <span className={`h-2 w-2 rounded-full ${tab.group === "input" ? "bg-emerald-500" : "bg-blue-500"}`} />
                <TabBadge group={tab.group} />
                <span className={`truncate max-w-[14rem] ${titleClass}`}>{tab.title}</span>
              </button>
              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  onTogglePin(tab.id);
                }}
                aria-label={isPinned ? `Unpin ${tab.title}` : `Pin ${tab.title}`}
                className={`h-9 px-2 text-gray-400 hover:text-gray-700 transition-opacity ${
                  isPinned ? "opacity-100" : "opacity-0 group-hover:opacity-100"
                }`}
              >
                <Pin className={`h-3.5 w-3.5 ${isPinned ? "text-blue-600" : ""}`} />
              </button>
              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  onCloseTab(tab.id);
                }}
                aria-label={`Close ${tab.title}`}
                className="h-9 px-2 text-gray-400 hover:text-gray-700 opacity-0 group-hover:opacity-100 transition-opacity"
              >
                ×
              </button>
              {tab.dirty && (
                <span className="absolute right-2 top-1/2 -translate-y-1/2 text-[10px] text-blue-600 group-hover:opacity-0 transition-opacity">
                  ●
                </span>
              )}
            </div>
          );
        })
        )}
      </div>
    </div>
  );
}

interface TabKeyboardNavProps {
  readonly tabs: readonly WorkspaceTab[];
  readonly activeTabId: string;
  readonly onCloseTab: (tabId: string) => void;
  readonly onTabChange: (tabId: string) => void;
}

function useTabKeyboardNavigation({
  tabs,
  activeTabId,
  onCloseTab,
  onTabChange,
}: TabKeyboardNavProps) {
  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    if (!shouldHandleTabShortcut(event)) return;
    handleTabShortcut({ event, tabs, activeTabId, onCloseTab, onTabChange });
  }, [activeTabId, onCloseTab, onTabChange, tabs]);

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [handleKeyDown]);
}

function shouldIgnoreKeyEvent(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) {
    return false;
  }
  const tag = target.tagName.toLowerCase();
  return tag === "input" || tag === "textarea" || target.isContentEditable;
}

function shouldHandleTabShortcut(event: KeyboardEvent): boolean {
  const isCmdOrCtrl = event.metaKey || event.ctrlKey;
  if (!isCmdOrCtrl) return false;
  return !shouldIgnoreKeyEvent(event.target);
}

function handleTabShortcut({
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

function cycleTab({
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

function focusTabIndex({
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

function getNextTabIndex(currentIndex: number, total: number, reverse: boolean): number {
  if (total === 0) return 0;
  if (currentIndex < 0) return 0;
  const direction = reverse ? -1 : 1;
  return (currentIndex + direction + total) % total;
}
