import type { WorkspaceTab } from "../components/unified/workspace/types";

export function createInputOverviewTab(): WorkspaceTab {
  return {
    id: "input-overview",
    kind: "input-overview",
    title: "Inputs",
    group: "input",
    pinned: false,
    dirty: false,
  };
}

export function createDiagramsTab(): WorkspaceTab {
  return {
    id: "artifact-diagrams",
    kind: "artifact-diagrams",
    title: "Diagrams",
    group: "artifact",
    pinned: false,
    dirty: false,
  };
}

export function createAdrTab(): WorkspaceTab {
  return {
    id: "artifact-adrs",
    kind: "artifact-adrs",
    title: "ADRs",
    group: "artifact",
    pinned: false,
    dirty: false,
  };
}

export function createIacTab(): WorkspaceTab {
  return {
    id: "artifact-iac",
    kind: "artifact-iac",
    title: "Infrastructure as Code",
    group: "artifact",
    pinned: false,
    dirty: false,
  };
}

export function createCostsTab(): WorkspaceTab {
  return {
    id: "artifact-costs",
    kind: "artifact-costs",
    title: "Cost Estimates",
    group: "artifact",
    pinned: false,
    dirty: false,
  };
}

export function createWafTab(): WorkspaceTab {
  return {
    id: "artifact-waf",
    kind: "artifact-waf",
    title: "WAF Checklist",
    group: "artifact",
    pinned: false,
    dirty: false,
  };
}

export function resolveTabIntent(tabIntent: string): WorkspaceTab | null {
  switch (tabIntent) {
    case "overview":
    case "inputs":
    case "workspace":
      return createInputOverviewTab();
    case "deliverables":
    case "diagrams":
      return createDiagramsTab();
    case "adrs":
      return createAdrTab();
    case "iac":
      return createIacTab();
    case "costs":
      return createCostsTab();
    case "waf":
      return createWafTab();
    default:
      return null;
  }
}

export function normalizeParam(value: string | null): string {
  if (value === null) {
    return "";
  }
  return value.trim().toLowerCase();
}

export function ProjectNotFound() {
  return (
    <div className="flex items-center justify-center h-screen">
      <div className="text-center">
        <h2 className="text-xl font-semibold text-foreground mb-2">Project not found</h2>
        <p className="text-secondary">The requested project could not be loaded.</p>
      </div>
    </div>
  );
}

export function ProjectLoading() {
  return (
    <div className="flex items-center justify-center h-screen">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand mx-auto mb-4" />
        <p className="text-secondary">Loading project...</p>
      </div>
    </div>
  );
}
