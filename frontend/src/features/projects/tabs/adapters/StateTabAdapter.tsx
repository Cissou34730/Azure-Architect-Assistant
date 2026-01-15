import { lazy } from "react";
import { useProjectContext } from "../../context/useProjectContext";

const STATE_PANEL_LAZY = lazy(() =>
  import("../../components/StatePanel").then((m) => ({
    default: m.StatePanel,
  })),
);

export function StateTabAdapter() {
  const { projectState, refreshState, loading } = useProjectContext();

  const STATE_PANEL = STATE_PANEL_LAZY;

  return (
    <STATE_PANEL
      projectState={projectState}
      onRefreshState={refreshState}
      loading={loading}
    />
  );
}
