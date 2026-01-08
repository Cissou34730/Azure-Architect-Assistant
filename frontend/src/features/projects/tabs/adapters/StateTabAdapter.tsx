import { lazy } from "react";
import { useProjectContext } from "../../context/ProjectContext";

const StatePanel = lazy(() =>
  import("../../components/StatePanel").then((m) => ({
    default: m.StatePanel,
  })),
);

export function StateTabAdapter() {
  const { projectState, refreshState, loading } = useProjectContext();

  return (
    <StatePanel
      projectState={projectState}
      onRefreshState={refreshState}
      loading={loading}
    />
  );
}
