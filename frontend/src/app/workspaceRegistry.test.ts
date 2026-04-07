import { describe, expect, it } from "vitest";
import {
  workspaceManifests,
  workspaceRouteModules,
  workspaceNavigationItems,
} from "./workspaceRegistry";

describe("workspace registry", () => {
  it("registers manifests for all phase 2 frontend features", () => {
    expect(workspaceManifests.map((manifest) => manifest.id)).toEqual([
      "projects",
      "agent",
      "diagrams",
      "knowledge",
      "ingestion",
      "settings",
    ]);
  });

  it("exposes route-backed workspace modules for static shell composition", () => {
    expect(
      workspaceRouteModules.map((manifest) => ({
        id: manifest.id,
        path: manifest.route.path,
      })),
    ).toEqual([
      { id: "projects", path: "/project" },
      { id: "knowledge", path: "/kb" },
      { id: "ingestion", path: "/kb-management" },
    ]);
  });

  it("surfaces navigation items from the manifest registry", () => {
    expect(
      workspaceNavigationItems.map((item) => ({
        id: item.id,
        to: item.to,
        label: item.label,
      })),
    ).toEqual([
      { id: "projects", to: "/project", label: "Projects" },
      { id: "knowledge", to: "/kb", label: "Knowledge Base" },
      { id: "ingestion", to: "/kb-management", label: "KB Management" },
    ]);
  });
});