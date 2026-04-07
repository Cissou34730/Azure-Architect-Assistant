import type { ReactElement } from "react";
import { ProjectHeader } from "./components/ProjectHeader";
import { LeftInputsArtifactsPanel } from "./components/unified/LeftInputsArtifactsPanel";
import { RightChatPanel } from "./components/unified/RightChatPanel";
import { CenterWorkspaceTabs } from "./components/unified/CenterWorkspaceTabs";
import type { WorkspaceTab } from "./components/unified/workspace/types";
import type { ProjectWorkspaceShellSlot } from "./workspaceDefinition";

const headerSlot: ProjectWorkspaceShellSlot = "header";
const leftSidebarSlot: ProjectWorkspaceShellSlot = "left-sidebar";
const centerSlot: ProjectWorkspaceShellSlot = "center";
const rightSidebarSlot: ProjectWorkspaceShellSlot = "right-sidebar";

interface ProjectWorkspaceShellRenderContext {
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
}

type ProjectWorkspaceShellRenderer = (
  context: ProjectWorkspaceShellRenderContext,
) => ReactElement;

const projectWorkspaceShellRenderers: Record<
  ProjectWorkspaceShellSlot,
  ProjectWorkspaceShellRenderer
> = {
  [headerSlot]: (context) => (
    <ProjectHeader
      onUploadClick={context.onUploadClick}
      onAdrClick={context.onAdrClick}
      onExportClick={context.onExportClick}
    />
  ),
  [leftSidebarSlot]: (context) => (
    <LeftInputsArtifactsPanel
      onToggle={context.onToggleLeft}
      onOpenTab={context.onOpenTab}
    />
  ),
  [centerSlot]: (context) => (
    <CenterWorkspaceTabs
      tabs={context.tabs}
      activeTabId={context.activeTabId}
      onTabChange={context.onTabChange}
      onCloseTab={context.onCloseTab}
      onOpenTab={context.onOpenTab}
      onTogglePin={context.onTogglePin}
      onReorderTab={context.onReorderTab}
    />
  ),
  [rightSidebarSlot]: (context) => (
    <RightChatPanel onToggle={context.onToggleRight} />
  ),
};

export const projectWorkspaceShellRendererSlots: readonly ProjectWorkspaceShellSlot[] = [
  headerSlot,
  leftSidebarSlot,
  centerSlot,
  rightSidebarSlot,
];

export function renderProjectWorkspaceShellContent(
  slot: ProjectWorkspaceShellSlot,
  context: ProjectWorkspaceShellRenderContext,
): ReactElement {
  return projectWorkspaceShellRenderers[slot](context);
}