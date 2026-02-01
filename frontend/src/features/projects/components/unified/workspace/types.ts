export type WorkspaceTabKind =
  | "input-overview"
  | "input-document"
  | "artifact-requirements"
  | "artifact-assumptions"
  | "artifact-questions"
  | "artifact-adrs"
  | "artifact-diagrams"
  | "artifact-findings"
  | "artifact-costs"
  | "artifact-iac"
  | "artifact-waf"
  | "artifact-traceability"
  | "artifact-candidates"
  | "artifact-iterations"
  | "artifact-mcp";

export type WorkspaceTabGroup = "input" | "artifact";

interface BaseWorkspaceTab {
  readonly id: string;
  readonly kind: WorkspaceTabKind;
  readonly title: string;
  readonly group: WorkspaceTabGroup;
  readonly pinned: boolean;
  readonly dirty: boolean;
}

export interface InputOverviewTab extends BaseWorkspaceTab {
  readonly kind: "input-overview";
  readonly group: "input";
}

export interface InputDocumentTab extends BaseWorkspaceTab {
  readonly kind: "input-document";
  readonly group: "input";
  readonly documentId: string;
}

export type ArtifactTab =
  | "artifact-requirements"
  | "artifact-assumptions"
  | "artifact-questions"
  | "artifact-adrs"
  | "artifact-diagrams"
  | "artifact-findings"
  | "artifact-costs"
  | "artifact-iac"
  | "artifact-waf"
  | "artifact-traceability"
  | "artifact-candidates"
  | "artifact-iterations"
  | "artifact-mcp";

export interface ArtifactWorkspaceTab extends BaseWorkspaceTab {
  readonly kind: ArtifactTab;
  readonly group: "artifact";
}

export type WorkspaceTab = InputOverviewTab | InputDocumentTab | ArtifactWorkspaceTab;
