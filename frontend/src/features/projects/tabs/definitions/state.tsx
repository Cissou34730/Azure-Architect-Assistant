import { ProjectTab } from "../types";
import { StateTabAdapter } from "../adapters/StateTabAdapter";

export const stateTab: ProjectTab = {
  id: "state",
  label: "State",
  path: "state",
  component: StateTabAdapter,
};
