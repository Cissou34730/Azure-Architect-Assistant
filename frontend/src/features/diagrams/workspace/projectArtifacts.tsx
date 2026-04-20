import { Network } from "lucide-react";
import type { ProjectWorkspaceStaticTabDefinition } from "../../projects/workspaceDefinition";

export const projectWorkspaceDiagramsContributorId = "diagrams-artifacts";

export const projectWorkspaceDiagramTabs: readonly ProjectWorkspaceStaticTabDefinition[] = [
  {
    id: "artifact-diagrams",
    kind: "artifact-diagrams",
    title: "Diagrams",
    group: "artifact",
    intents: ["deliverables", "diagrams"],
    treeEntry: { label: "Diagrams", icon: Network, color: "blue" },
    badgeKey: "diagrams",
    category: "architecture",
  },
];
