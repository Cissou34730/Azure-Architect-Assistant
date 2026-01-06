import { lazy } from "react";

const DiagramSetViewer = lazy(() => import("../../../../components/diagrams/DiagramSetViewer").then(m => ({ default: m.DiagramSetViewer })));

export function DiagramsTabAdapter() {
  // Diagrams currently has hardcoded ID in original file, keeping it for now
  return <DiagramSetViewer diagramSetId="aa57f645-e736-430e-bab0-e8c6a953a047" />;
}
