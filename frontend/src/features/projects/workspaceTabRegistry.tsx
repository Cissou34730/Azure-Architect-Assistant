import type { ReactElement } from "react";
import { projectWorkspaceAgentRenderers } from "../agent/workspace/projectArtifactRenderers";
import { projectWorkspaceDiagramRenderers } from "../diagrams/workspace/projectArtifactRenderers";
import { projectWorkspaceStaticTabs } from "./workspace.manifest";
import { projectWorkspaceChecklistRenderers } from "./workspace/checklistsArtifactRenderers";
import {
  projectWorkspaceInputContributorId,
  projectWorkspaceInputRenderers,
} from "./workspace/projectsInputs.tsx";
import type {
  ProjectWorkspaceStaticTabKind,
  ProjectWorkspaceStaticTabRenderContext,
  ProjectWorkspaceStaticTabRenderer,
} from "./workspaceTabRenderTypes";

const projectWorkspaceStaticTabRenderers = {
  ...projectWorkspaceInputRenderers,
  ...projectWorkspaceAgentRenderers,
  ...projectWorkspaceDiagramRenderers,
  ...projectWorkspaceChecklistRenderers,
} satisfies Record<ProjectWorkspaceStaticTabKind, ProjectWorkspaceStaticTabRenderer>;

export const projectWorkspaceRendererContributorIds: readonly string[] = [
  projectWorkspaceInputContributorId,
  "agent-artifacts",
  "diagrams-artifacts",
  "checklists-artifacts",
];

export const projectWorkspaceStaticTabRendererKinds = projectWorkspaceStaticTabs.map(
  (tabDefinition) => tabDefinition.id,
);

export function renderProjectWorkspaceStaticTabContent(
  tabKind: ProjectWorkspaceStaticTabKind,
  context: ProjectWorkspaceStaticTabRenderContext,
): ReactElement {
  return projectWorkspaceStaticTabRenderers[tabKind](context);
}