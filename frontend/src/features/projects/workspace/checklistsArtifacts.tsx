import { ListChecks } from "lucide-react";
import type { ProjectWorkspaceStaticTabDefinition } from "../workspaceDefinition";

export const projectWorkspaceChecklistContributorId = "checklists-artifacts";

export const projectWorkspaceChecklistTabs: readonly ProjectWorkspaceStaticTabDefinition[] = [
  {
    id: "artifact-waf",
    kind: "artifact-waf",
    title: "WAF Checklist",
    group: "artifact",
    intents: ["waf"],
    treeEntry: { label: "WAF Checklist", icon: ListChecks, color: "blue" },
    badgeKey: "waf",
    category: "validation",
  },
];
