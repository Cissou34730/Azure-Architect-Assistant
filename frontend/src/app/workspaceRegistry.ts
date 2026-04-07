import type {
  WorkspaceManifest,
  WorkspaceNavigationItem,
  WorkspaceRouteManifest,
} from "./workspaceManifest";
import { agentWorkspaceManifest } from "../features/agent/workspace.manifest";
import { diagramsWorkspaceManifest } from "../features/diagrams/workspace.manifest";
import { ingestionWorkspaceManifest } from "../features/ingestion/workspace.manifest";
import { knowledgeWorkspaceManifest } from "../features/knowledge/workspace.manifest";
import { projectsWorkspaceManifest } from "../features/projects/workspace.manifest";
import { settingsWorkspaceManifest } from "../features/settings/workspace.manifest";

interface WorkspaceManifestWithRoute extends WorkspaceManifest {
  readonly route: WorkspaceRouteManifest;
}

function hasRoute(
  workspaceManifest: WorkspaceManifest,
): workspaceManifest is WorkspaceManifestWithRoute {
  return workspaceManifest.route !== undefined;
}

export const workspaceManifests: readonly WorkspaceManifest[] = [
  projectsWorkspaceManifest,
  agentWorkspaceManifest,
  diagramsWorkspaceManifest,
  knowledgeWorkspaceManifest,
  ingestionWorkspaceManifest,
  settingsWorkspaceManifest,
];

export const workspaceRouteModules: readonly WorkspaceManifestWithRoute[] =
  workspaceManifests.filter(hasRoute);

export const workspaceNavigationItems: readonly WorkspaceNavigationItem[] =
  workspaceRouteModules.map((workspaceManifest) => ({
    id: workspaceManifest.id,
    to: workspaceManifest.route.path,
    label: workspaceManifest.route.navLabel,
    ariaLabel: workspaceManifest.route.ariaLabel,
  }));

export const workspaceManifestById = {
  projects: projectsWorkspaceManifest,
  agent: agentWorkspaceManifest,
  diagrams: diagramsWorkspaceManifest,
  knowledge: knowledgeWorkspaceManifest,
  ingestion: ingestionWorkspaceManifest,
  settings: settingsWorkspaceManifest,
} satisfies Record<WorkspaceManifest["id"], WorkspaceManifest>;