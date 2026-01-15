import { lazy } from "react";

const DIAGRAM_SET_VIEWER_LAZY = lazy(() =>
  import("../../../../components/diagrams/DiagramSetViewer").then((m) => ({
    default: m.DiagramSetViewer,
  })),
);

export function DiagramsTabAdapter() {
  const DIAGRAM_SET_VIEWER = DIAGRAM_SET_VIEWER_LAZY;
  return (
    <DIAGRAM_SET_VIEWER diagramSetId="aa57f645-e736-430e-bab0-e8c6a953a047" />
  );
}
