import { lazy } from "react";
import { useProjectContext } from "../../context/useProjectContext";

// eslint-disable-next-line @typescript-eslint/naming-convention
const AaaWorkspace = lazy(() =>
  import("../../../aaa/AaaWorkspace").then((m) => ({ default: m.default })),
);

export function AaaTabAdapter() {
  const { selectedProject } = useProjectContext();
  if (selectedProject === null) return null;

  return <AaaWorkspace />;
}
