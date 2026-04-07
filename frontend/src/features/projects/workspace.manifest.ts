import type { WorkspaceManifest } from "../../app/workspaceManifest";
import { projectWorkspaceAgentTabs } from "../agent/workspace/projectArtifacts";
import { projectWorkspaceDiagramTabs } from "../diagrams/workspace/projectArtifacts";
import type { WorkspaceTab } from "./components/unified/workspace/types";
import { projectWorkspaceChecklistTabs } from "./workspace/checklistsArtifacts";
import {
  projectWorkspaceInputContributorId,
  projectWorkspaceInputTreeEntries as projectWorkspaceInputTreeEntriesSource,
  projectWorkspaceInputTabs,
} from "./workspace/projectsInputs.tsx";
import {
  projectWorkspaceShellContributorId,
  projectWorkspaceShellSections,
} from "./workspace/projectsShell";
import type {
  ProjectWorkspaceArtifactTabDefinition,
  ProjectWorkspaceDefinition,
  ProjectWorkspaceShellSection,
  ProjectWorkspaceShellSlot,
  ProjectWorkspaceStaticTabDefinition,
  ProjectWorkspaceStaticTabId,
} from "./workspaceDefinition";

export { createProjectDocumentTab } from "./workspaceTabFactories";

interface ProjectWorkspaceManifest extends WorkspaceManifest {
  readonly workspace: ProjectWorkspaceDefinition;
}

export const projectWorkspaceContributorIds: readonly string[] = [
  projectWorkspaceShellContributorId,
  projectWorkspaceInputContributorId,
  "agent-artifacts",
  "diagrams-artifacts",
  "checklists-artifacts",
];

const projectWorkspaceStaticTabDefinitions: readonly ProjectWorkspaceStaticTabDefinition[] = [
  ...projectWorkspaceInputTabs,
  ...projectWorkspaceAgentTabs,
  ...projectWorkspaceDiagramTabs,
  ...projectWorkspaceChecklistTabs,
];

export const projectsWorkspaceManifest: ProjectWorkspaceManifest = {
  id: "projects",
  title: "Projects",
  summary: "Project list and unified workspace shell.",
  route: {
    path: "/project",
    navLabel: "Projects",
    ariaLabel: "View architecture projects",
    importRoute: () => import("./pages/ProjectsPage"),
  },
  workspace: {
    defaultTabId: "input-overview",
    shellSections: projectWorkspaceShellSections,
    inputTreeEntries: projectWorkspaceInputTreeEntriesSource,
    staticTabs: projectWorkspaceStaticTabDefinitions,
  },
};

export const projectWorkspaceInputTreeEntries =
  projectsWorkspaceManifest.workspace.inputTreeEntries;

export const projectWorkspaceStaticTabs =
  projectsWorkspaceManifest.workspace.staticTabs;

export const projectWorkspaceArtifactTreeEntries =
  projectWorkspaceStaticTabs.filter(isArtifactWorkspaceTabDefinition);

export const projectWorkspaceDefaultTabs: readonly WorkspaceTab[] = [
  createProjectWorkspaceTab(projectsWorkspaceManifest.workspace.defaultTabId),
];

export function createProjectWorkspaceTab(
  tabId: ProjectWorkspaceStaticTabId,
): WorkspaceTab {
  const tabDefinition = projectWorkspaceStaticTabs.find(
    (definition) => definition.id === tabId,
  );
  if (tabDefinition === undefined) {
    throw new Error(`Unknown project workspace tab: ${tabId}`);
  }

  if (isArtifactWorkspaceTabDefinition(tabDefinition)) {
    return {
      id: tabDefinition.id,
      kind: tabDefinition.kind,
      title: tabDefinition.title,
      group: "artifact",
      pinned: false,
      dirty: false,
    };
  }

  return {
    id: tabDefinition.id,
    kind: "input-overview",
    title: tabDefinition.title,
    group: "input",
    pinned: false,
    dirty: false,
  };
}

export function resolveProjectWorkspaceTabIntent(
  tabIntent: string,
): WorkspaceTab | null {
  const normalizedIntent = tabIntent.trim().toLowerCase();
  if (normalizedIntent === "") {
    return null;
  }

  const tabDefinition = projectWorkspaceStaticTabs.find((definition) =>
    definition.intents.includes(normalizedIntent),
  );

  return tabDefinition === undefined
    ? null
    : createProjectWorkspaceTab(tabDefinition.id);
}

export function getProjectWorkspaceShellSection(
  slot: ProjectWorkspaceShellSlot,
): ProjectWorkspaceShellSection {
  const shellSection = projectsWorkspaceManifest.workspace.shellSections.find(
    (currentSection) => currentSection.slot === slot,
  );
  if (shellSection === undefined) {
    throw new Error(`Missing project workspace shell section: ${slot}`);
  }
  return shellSection;
}

function isArtifactWorkspaceTabDefinition(
  definition: ProjectWorkspaceStaticTabDefinition,
): definition is ProjectWorkspaceArtifactTabDefinition {
  return definition.group === "artifact";
}