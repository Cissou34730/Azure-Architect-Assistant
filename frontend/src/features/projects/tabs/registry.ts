import { ProjectTab } from "./types";

// Registry to hold tab definitions
const registry: ProjectTab[] = [];

export function registerTab(tab: ProjectTab) {
  // Prevent duplicates
  if (!registry.find((t) => t.id === tab.id)) {
    registry.push(tab);
  }
}

export function getTabs(): ProjectTab[] {
  return [...registry];
}
