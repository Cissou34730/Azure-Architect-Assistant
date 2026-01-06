import { ProjectTab } from "../types";
import { DiagramSetViewer } from "../../../../components/diagrams/DiagramSetViewer";

const DiagramsComponent = () => {
  // Diagrams currently has hardcoded ID in original file, keeping it for now
  return <DiagramSetViewer diagramSetId="aa57f645-e736-430e-bab0-e8c6a953a047" />;
};

export const diagramsTab: ProjectTab = {
  id: "diagrams",
  label: "Diagrams",
  path: "diagrams",
  component: DiagramsComponent,
};
