import { ProjectTab } from "../types";
import { DiagramsTabAdapter } from "../adapters/DiagramsTabAdapter";

export const diagramsTab: ProjectTab = {
  id: "diagrams",
  label: "Diagrams",
  path: "diagrams",
  component: DiagramsTabAdapter,
};
