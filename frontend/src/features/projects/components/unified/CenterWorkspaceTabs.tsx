import { useMemo, useEffect, useState, useCallback } from "react";
import { useProjectStateContext } from "../../context/useProjectStateContext";
import type { WorkspaceTab } from "./workspace/types";
import { WorkspaceTabContent } from "./workspace/WorkspaceTabContent";
import {
  handleTabShortcut,
  shouldHandleTabShortcut,
} from "./CenterWorkspaceTabsKeyboard";
import { TabStrip } from "./TabStrip";

interface CenterWorkspaceTabsProps {
  readonly tabs: readonly WorkspaceTab[];
  readonly activeTabId: string;
  readonly onTabChange: (tabId: string) => void;
  readonly onCloseTab: (tabId: string) => void;
  readonly onOpenTab: (tab: WorkspaceTab) => void;
  readonly onTogglePin: (tabId: string) => void;
  readonly onReorderTab: (sourceId: string, targetId: string) => void;
}

export function CenterWorkspaceTabs({
  tabs,
  activeTabId,
  onTabChange,
  onCloseTab,
  onOpenTab,
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
    <div className="flex flex-col h-full bg-card border border-border rounded-xl overflow-hidden shadow-sm">
      <div className="flex items-center justify-between px-3 py-2 bg-foreground text-inverse text-xs font-semibold uppercase tracking-wide">
        <span>Workspace Tabs</span>
        <span className="text-dim">{tabs.length} open</span>
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

      <div className="flex-1 overflow-hidden bg-card">
        {hasActiveTab ? (
          <WorkspaceTabContent
            tab={activeTab}
            documents={documents}
            hasArtifacts={hasArtifacts}
            onOpenTab={onOpenTab}
          />
        ) : (
          <div className="h-full flex items-center justify-center text-sm text-dim">
            Select an input or artifact from the left panel.
          </div>
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



