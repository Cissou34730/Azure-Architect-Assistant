import { lazy } from "react";
import { useProjectContext } from "../../context/useProjectContext";

const AaaWorkspace = lazy(() =>
  import("../../../aaa/AaaWorkspace").then((m) => ({ default: m.default })),
);

export function AaaTabAdapter() {
  const { selectedProject } = useProjectContext();
  if (!selectedProject) return null;

  return <AaaWorkspace />;
}
