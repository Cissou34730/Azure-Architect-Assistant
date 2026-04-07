import type { ComponentType } from "react";

export interface WorkspaceRouteManifest {
  readonly path: string;
  readonly navLabel: string;
  readonly ariaLabel: string;
  readonly importRoute: () => Promise<{ default: ComponentType }>;
}

export interface WorkspaceManifest {
  readonly id:
    | "projects"
    | "agent"
    | "diagrams"
    | "knowledge"
    | "ingestion"
    | "settings";
  readonly title: string;
  readonly summary: string;
  readonly route?: WorkspaceRouteManifest;
}

export interface WorkspaceNavigationItem {
  readonly id: WorkspaceManifest["id"];
  readonly to: string;
  readonly label: string;
  readonly ariaLabel: string;
}