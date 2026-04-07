import type { LucideIcon } from "lucide-react";
import type { ArtifactTab } from "./components/unified/workspace/types";

export type ProjectWorkspaceShellSlot =
  | "header"
  | "left-sidebar"
  | "center"
  | "right-sidebar";

export interface ProjectWorkspaceShellSection {
  readonly id: string;
  readonly slot: ProjectWorkspaceShellSlot;
  readonly collapsedTitle?: string;
  readonly minWidth?: number;
  readonly maxWidth?: number;
  readonly className?: string;
}

export type ProjectWorkspaceStaticTabId = "input-overview" | ArtifactTab;

export type ProjectWorkspaceArtifactBadgeKey =
  | "requirements"
  | "assumptions"
  | "questions"
  | "adrs"
  | "diagrams"
  | "findings"
  | "costs"
  | "iac"
  | "waf"
  | "traceability"
  | "candidates"
  | "iterations"
  | "mcpQueries";

export interface ProjectWorkspaceTreeEntry {
  readonly label: string;
  readonly icon: LucideIcon;
  readonly color: "blue" | "emerald";
}

export interface ProjectWorkspaceInputTreeEntry extends ProjectWorkspaceTreeEntry {
  readonly id: string;
  readonly tabId: "input-overview";
  readonly badgeKey: "inputs" | "clarifications";
}

export interface ProjectWorkspaceInputTabDefinition {
  readonly id: "input-overview";
  readonly kind: "input-overview";
  readonly title: string;
  readonly group: "input";
  readonly intents: readonly string[];
  readonly treeEntry: ProjectWorkspaceTreeEntry;
}

export interface ProjectWorkspaceArtifactTabDefinition {
  readonly id: ArtifactTab;
  readonly kind: ArtifactTab;
  readonly title: string;
  readonly group: "artifact";
  readonly intents: readonly string[];
  readonly treeEntry: ProjectWorkspaceTreeEntry;
  readonly badgeKey: ProjectWorkspaceArtifactBadgeKey;
}

export type ProjectWorkspaceStaticTabDefinition =
  | ProjectWorkspaceInputTabDefinition
  | ProjectWorkspaceArtifactTabDefinition;

export interface ProjectWorkspaceDefinition {
  readonly defaultTabId: "input-overview";
  readonly shellSections: readonly ProjectWorkspaceShellSection[];
  readonly inputTreeEntries: readonly ProjectWorkspaceInputTreeEntry[];
  readonly staticTabs: readonly ProjectWorkspaceStaticTabDefinition[];
}