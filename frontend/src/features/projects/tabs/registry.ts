import { ProjectTab } from "./types";

// Registry to hold tab definitions
const registry: ProjectTab[] = [];

export function registerTab(tab: ProjectTab) {
  // Prevent duplicates
  const existing = registry.find((t) => t.id === tab.id);
  if (existing === undefined) {
    registry.push(tab);
  }
}

export function getTabs(): ProjectTab[] {
  return [...registry];
}
