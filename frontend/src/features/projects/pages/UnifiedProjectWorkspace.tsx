import { ProjectHeader } from "../components/ProjectHeader";
import { LeftInputsArtifactsPanel } from "../components/unified/LeftInputsArtifactsPanel";
import { RightChatPanel } from "../components/unified/RightChatPanel";
import { ResizableSidePanel } from "../components/unified/ResizableSidePanel";
import { CenterWorkspaceTabs } from "../components/unified/CenterWorkspaceTabs";
import type { WorkspaceTab } from "../components/unified/workspace/types";

interface UnifiedProjectWorkspaceProps {
  readonly leftPanelOpen: boolean;
  readonly rightPanelOpen: boolean;
  readonly onToggleLeft: () => void;
  readonly onToggleRight: () => void;
  readonly onUploadClick: () => void;
  readonly onGenerateClick: () => void;
  readonly onAdrClick: () => void;
  readonly onExportClick: () => void;
  readonly tabs: readonly WorkspaceTab[];
  readonly activeTabId: string;
  readonly onTabChange: (tabId: string) => void;
  readonly onCloseTab: (tabId: string) => void;
  readonly onOpenTab: (tab: WorkspaceTab) => void;
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
  onGenerateClick,
  onAdrClick,
  onExportClick,
  tabs,
  activeTabId,
  onTabChange,
  onCloseTab,
  onOpenTab,
  leftPanelWidth,
  rightPanelWidth,
  onResizeLeft,
  onResizeRight,
}: UnifiedProjectWorkspaceProps) {
  return (
    <div className="flex flex-col h-screen overflow-hidden bg-slate-100">
      <ProjectHeader
        onUploadClick={onUploadClick}
        onGenerateClick={onGenerateClick}
        onAdrClick={onAdrClick}
        onExportClick={onExportClick}
      />

      <div className="flex-1 flex overflow-hidden">
        <ResizableSidePanel
          side="left"
          isOpen={leftPanelOpen}
          width={leftPanelWidth}
          minWidth={260}
          maxWidth={480}
          onResize={onResizeLeft}
          onToggle={onToggleLeft}
          collapsedTitle="Show inputs & artifacts"
          className="bg-slate-50"
        >
          <LeftInputsArtifactsPanel
            onToggle={onToggleLeft}
            onOpenTab={onOpenTab}
          />
        </ResizableSidePanel>

        <div className="flex-1 overflow-hidden px-4 py-4 bg-white panel-scroll-scope">
          <CenterWorkspaceTabs
            tabs={tabs}
            activeTabId={activeTabId}
            onTabChange={onTabChange}
            onCloseTab={onCloseTab}
          />
        </div>

        <ResizableSidePanel
          side="right"
          isOpen={rightPanelOpen}
          width={rightPanelWidth}
          minWidth={280}
          maxWidth={520}
          onResize={onResizeRight}
          onToggle={onToggleRight}
          collapsedTitle="Show chat"
          className="bg-slate-50"
        >
          <RightChatPanel onToggle={onToggleRight} />
        </ResizableSidePanel>
      </div>
    </div>
  );
}
