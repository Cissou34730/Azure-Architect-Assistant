import { ProjectTab } from "../types";
import { useProjectContext } from "../../context/ProjectContext";
import { StatePanel } from "../../components/StatePanel";

const StateComponent = () => {
  const { projectState, refreshState, loading } = useProjectContext();

  return (
    <StatePanel
      projectState={projectState}
      onRefreshState={refreshState}
      loading={loading}
    />
  );
};

export const stateTab: ProjectTab = {
  id: "state",
  label: "State",
  path: "state",
  component: StateComponent,
};
