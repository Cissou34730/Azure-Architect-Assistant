import { WafChecklistView } from "../components/unified/workspace/WafChecklistView";
import type { ProjectWorkspaceStaticTabRenderer } from "../workspaceTabRenderTypes";

export const projectWorkspaceChecklistRenderers = {
  ["artifact-waf"]: ({ projectState }) => <WafChecklistView projectState={projectState} />,
} satisfies Partial<Record<string, ProjectWorkspaceStaticTabRenderer>>;