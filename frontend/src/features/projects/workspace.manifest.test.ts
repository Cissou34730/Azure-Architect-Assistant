import { describe, expect, it } from "vitest";
import type { ReferenceDocument } from "./types/api-artifacts";
import {
  createProjectDocumentTab,
  createProjectWorkspaceTab,
  projectWorkspaceContributorIds,
  projectsWorkspaceManifest,
  resolveProjectWorkspaceTabIntent,
} from "./workspace.manifest";
import {
  projectWorkspaceRendererContributorIds,
  projectWorkspaceStaticTabRendererKinds,
} from "./workspaceTabRegistry";
import { projectWorkspaceShellRendererSlots } from "./workspaceShellRegistry";

describe("projects workspace manifest", () => {
  it("defines the unified workspace shell sections in static registry order", () => {
    expect(
      projectsWorkspaceManifest.workspace.shellSections.map((section) => ({
        id: section.id,
        slot: section.slot,
      })),
    ).toEqual([
      { id: "project-header", slot: "header" },
      { id: "project-tree", slot: "left-sidebar" },
      { id: "workspace-tabs", slot: "center" },
      { id: "project-chat", slot: "right-sidebar" },
    ]);
  });

  it("drives default tabs and route intents from static tab definitions", () => {
    expect(projectsWorkspaceManifest.workspace.defaultTabId).toBe("input-overview");
    expect(createProjectWorkspaceTab("artifact-adrs")).toEqual({
      id: "artifact-adrs",
      kind: "artifact-adrs",
      title: "ADRs",
      group: "artifact",
      pinned: false,
      dirty: false,
    });
    expect(resolveProjectWorkspaceTabIntent("workspace")).toEqual({
      id: "input-overview",
      kind: "input-overview",
      title: "Inputs",
      group: "input",
      pinned: false,
      dirty: false,
    });
    expect(resolveProjectWorkspaceTabIntent("costs")).toEqual({
      id: "artifact-costs",
      kind: "artifact-costs",
      title: "Cost Estimates",
      group: "artifact",
      pinned: false,
      dirty: false,
    });
    expect(resolveProjectWorkspaceTabIntent("unknown")).toBeNull();
  });

  it("creates input document tabs from uploaded project documents", () => {
    const document: ReferenceDocument = {
      id: "doc-1",
      category: "reference",
      title: "Reference Architecture",
      analysisStatus: "analyzed",
      parseStatus: "parsed",
    };

    expect(createProjectDocumentTab(document)).toEqual({
      id: "input-document-doc-1",
      kind: "input-document",
      title: "Reference Architecture",
      group: "input",
      documentId: "doc-1",
      pinned: false,
      dirty: false,
    });
  });

  it("covers every manifest-defined static tab with the workspace tab registry", () => {
    expect(projectWorkspaceStaticTabRendererKinds).toEqual(
      projectsWorkspaceManifest.workspace.staticTabs.map((tabDefinition) => tabDefinition.id),
    );
  });

  it("assembles workspace shell and tab contributions from multiple feature-owned registries", () => {
    expect(projectWorkspaceContributorIds).toEqual([
      "projects-shell",
      "projects-inputs",
      "agent-artifacts",
      "diagrams-artifacts",
      "checklists-artifacts",
    ]);
    expect(projectWorkspaceRendererContributorIds).toEqual([
      "projects-inputs",
      "agent-artifacts",
      "diagrams-artifacts",
      "checklists-artifacts",
    ]);
  });

  it("covers every shell section with a feature-owned shell renderer registry", () => {
    expect(projectWorkspaceShellRendererSlots).toEqual(
      projectsWorkspaceManifest.workspace.shellSections.map((section) => section.slot),
    );
  });
});