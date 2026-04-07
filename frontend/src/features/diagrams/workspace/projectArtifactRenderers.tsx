import { DiagramGallery } from "../../projects/components/deliverables";
import type { ProjectWorkspaceStaticTabRenderer } from "../../projects/workspaceTabRenderTypes";

export const projectWorkspaceDiagramRenderers = {
  ["artifact-diagrams"]: ({ projectState }) => <DiagramGallery diagrams={projectState.diagrams} />,
} satisfies Partial<Record<string, ProjectWorkspaceStaticTabRenderer>>;