import type { ReactElement } from "react";
import type { WorkspaceTab } from "./components/unified/workspace/types";
import type { ReferenceDocument } from "./types/api-artifacts";
import type { ProjectState } from "./types/api-project";
import type { ProjectWorkspaceStaticTabId } from "./workspaceDefinition";

export type ProjectWorkspaceStaticTabKind = ProjectWorkspaceStaticTabId;

export interface ProjectWorkspaceStaticTabRenderContext {
  readonly projectState: ProjectState;
  readonly documents: readonly ReferenceDocument[];
  readonly hasArtifacts: boolean;
  readonly onOpenTab: (tab: WorkspaceTab) => void;
}

export type ProjectWorkspaceStaticTabRenderer = (
  context: ProjectWorkspaceStaticTabRenderContext,
) => ReactElement;