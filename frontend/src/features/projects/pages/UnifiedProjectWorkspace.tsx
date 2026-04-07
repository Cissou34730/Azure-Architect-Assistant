import { ResizableSidePanel } from "../components/unified/ResizableSidePanel";
import type { WorkspaceTab } from "../components/unified/workspace/types";
import { renderProjectWorkspaceShellContent } from "../workspaceShellRegistry";
import { getProjectWorkspaceShellSection } from "../workspace.manifest";

const headerSection = getProjectWorkspaceShellSection("header");
const leftSidebarSection = getProjectWorkspaceShellSection("left-sidebar");
const centerSection = getProjectWorkspaceShellSection("center");
const rightSidebarSection = getProjectWorkspaceShellSection("right-sidebar");

interface UnifiedProjectWorkspaceProps {
  readonly leftPanelOpen: boolean;
  readonly rightPanelOpen: boolean;
  readonly onToggleLeft: () => void;
  readonly onToggleRight: () => void;
  readonly onUploadClick: () => void;
  readonly onAdrClick: () => void;
  readonly onExportClick: () => void;
  readonly tabs: readonly WorkspaceTab[];
  readonly activeTabId: string;
  readonly onTabChange: (tabId: string) => void;
  readonly onCloseTab: (tabId: string) => void;
  readonly onOpenTab: (tab: WorkspaceTab) => void;
  readonly onTogglePin: (tabId: string) => void;
  readonly onReorderTab: (sourceId: string, targetId: string) => void;
  readonly leftPanelWidth: number;
  readonly rightPanelWidth: number;
  readonly onResizeLeft: (width: number) => void;
  readonly onResizeRight: (width: number) => void;
}

export function UnifiedProjectWorkspace({
  leftPanelOpen,
  rightPanelOpen,
  onToggleLeft,
  onToggleRight,
  onUploadClick,
  onAdrClick,
  onExportClick,
  tabs,
  activeTabId,
  onTabChange,
  onCloseTab,
  onOpenTab,
  onTogglePin,
  onReorderTab,
  leftPanelWidth,
  rightPanelWidth,
  onResizeLeft,
  onResizeRight,
}: UnifiedProjectWorkspaceProps) {
  const shellContext = {
    onToggleLeft,
    onToggleRight,
    onUploadClick,
    onAdrClick,
    onExportClick,
    tabs,
    activeTabId,
    onTabChange,
    onCloseTab,
    onOpenTab,
    onTogglePin,
    onReorderTab,
  };

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-surface">
      <div data-workspace-shell={headerSection.id}>
        {renderProjectWorkspaceShellContent("header", shellContext)}
      </div>

      <div className="flex-1 flex overflow-hidden">
        <ResizableSidePanel
          side="left"
          isOpen={leftPanelOpen}
          width={leftPanelWidth}
          minWidth={leftSidebarSection.minWidth ?? 260}
          maxWidth={leftSidebarSection.maxWidth ?? 480}
          onResize={onResizeLeft}
          onToggle={onToggleLeft}
          collapsedTitle={leftSidebarSection.collapsedTitle ?? "Show inputs & artifacts"}
          className={leftSidebarSection.className}
        >
          {renderProjectWorkspaceShellContent("left-sidebar", shellContext)}
        </ResizableSidePanel>

        <div
          className={centerSection.className ?? "flex-1 overflow-hidden px-4 py-4 bg-card panel-scroll-scope"}
          data-workspace-shell={centerSection.id}
        >
          {renderProjectWorkspaceShellContent("center", shellContext)}
        </div>

        <ResizableSidePanel
          side="right"
          isOpen={rightPanelOpen}
          width={rightPanelWidth}
          minWidth={rightSidebarSection.minWidth ?? 280}
          maxWidth={rightSidebarSection.maxWidth ?? 520}
          onResize={onResizeRight}
          onToggle={onToggleRight}
          collapsedTitle={rightSidebarSection.collapsedTitle ?? "Show chat"}
          className={rightSidebarSection.className}
        >
          {renderProjectWorkspaceShellContent("right-sidebar", shellContext)}
        </ResizableSidePanel>
      </div>
    </div>
  );
}


